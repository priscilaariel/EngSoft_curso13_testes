import hashlib
import hmac
import time
from typing import Callable, Optional
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import Settings
from app.db import Database
from app.provider import ProviderClient
from app.repository import InsufficientCredits, Repository, UserNotFound
from app.schemas import USER_ID_PATTERN, JobCreate, JobStatus, UserUpdate, WebhookEvent
from app.service import JobCreationFailed, JobService


def create_app(
    settings: Optional[Settings] = None,
    http_client: Optional[httpx.Client] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> FastAPI:
    settings = settings or Settings.from_env()
    repo = Repository(Database(settings.db_path))
    http = http_client or httpx.Client(timeout=settings.provider_timeout_seconds)
    provider = ProviderClient(
        http,
        settings.provider_base_url,
        settings.provider_api_key,
        max_attempts=settings.provider_max_attempts,
        backoff_seconds=settings.provider_backoff_seconds,
        sleep=sleep,
    )
    service = JobService(repo, provider)

    app = FastAPI(title="Render Jobs API", version="1.0.0")
    app.state.repo = repo
    app.state.service = service

    # ------------------------------------------------------------ usuários
    @app.put("/users/{user_id}")
    def put_user(body: UserUpdate, user_id: str = Path(pattern=USER_ID_PATTERN)):
        return repo.put_user(user_id, body.credits)

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        user = repo.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user_not_found")
        return user

    # ---------------------------------------------------------------- jobs
    @app.post("/jobs", status_code=201)
    def create_job(body: JobCreate):
        try:
            return service.create_job(body.user_id, body.prompt, body.resolution)
        except UserNotFound:
            raise HTTPException(status_code=404, detail="user_not_found")
        except InsufficientCredits:
            raise HTTPException(status_code=402, detail="insufficient_credits")
        except JobCreationFailed as failure:
            return JSONResponse(
                status_code=failure.error.http_status,
                content={"detail": failure.error.code, "job_id": failure.job_id},
            )

    @app.get("/jobs/{job_id}")
    def get_job(job_id: UUID):
        job = repo.get_job(str(job_id))
        if job is None:
            raise HTTPException(status_code=404, detail="job_not_found")
        return job

    @app.get("/jobs")
    def list_jobs(
        user_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return repo.list_jobs(user_id, status, limit, offset)

    # ------------------------------------------------------------- webhook
    @app.post("/webhooks/provider")
    async def provider_webhook(request: Request):
        raw = await request.body()
        received = request.headers.get("X-Signature", "")
        expected = hmac.new(settings.webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected.encode(), received.encode()):
            raise HTTPException(status_code=401, detail="invalid_signature")

        try:
            event = WebhookEvent.model_validate_json(raw)
        except ValidationError:
            return JSONResponse(status_code=422, content={"detail": "invalid_payload"})

        result = repo.apply_provider_result(event.id, event.status, event.image_url, event.error)
        if result is None:
            raise HTTPException(status_code=404, detail="job_not_found")
        return {"result": result}

    return app


def build_default_app() -> FastAPI:
    return create_app()
