"""Fixtures compartilhadas pelas suítes de teste de integração.

O Provedor externo é substituído por um FakeProvider baseado em httpx.MockTransport:
a API usa o cliente HTTP real, só a rede é simulada. O banco é SQLite em memória.
"""
import hashlib
import hmac
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SECRET = "segredo-de-teste"
API_KEY = "chave-de-teste"
BASE_URL = "https://provedor.test"


class FakeProvider:
    """Provedor simulado. Por padrão aceita tudo com 202 e ids gen_1, gen_2...

    Use enqueue() para programar respostas (httpx.Response) ou exceções
    para as próximas chamadas, na ordem em que serão consumidas.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self._script: list = []
        self._counter = 0

    def enqueue(self, *items):
        self._script.extend(items)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._script:
            item = self._script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        self._counter += 1
        return httpx.Response(202, json={"id": f"gen_{self._counter}"})

    @property
    def calls(self) -> int:
        return len(self.requests)

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def app(provider, sleeps):
    settings = Settings(
        db_path=":memory:",
        provider_base_url=BASE_URL,
        provider_api_key=API_KEY,
        webhook_secret=SECRET,
        provider_max_attempts=3,
        provider_backoff_seconds=0.5,
        provider_timeout_seconds=5.0,
    )
    http_client = httpx.Client(transport=httpx.MockTransport(provider.handler))
    return create_app(settings=settings, http_client=http_client, sleep=sleeps.append)


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------- helpers

def sign(raw: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def make_user(client, user_id="ana", credits=10):
    response = client.put(f"/users/{user_id}", json={"credits": credits})
    assert response.status_code == 200
    return response.json()


def credits_of(client, user_id="ana") -> int:
    return client.get(f"/users/{user_id}").json()["credits"]


def create_job(client, user_id="ana", prompt="um gato astronauta", **extra):
    return client.post("/jobs", json={"user_id": user_id, "prompt": prompt, **extra})


def send_webhook(client, payload: dict, *, secret: str = SECRET, raw: bytes | None = None, headers=None):
    body = raw if raw is not None else json.dumps(payload).encode()
    final_headers = {"Content-Type": "application/json", "X-Signature": sign(body, secret)}
    if headers is not None:
        final_headers = headers
    return client.post("/webhooks/provider", content=body, headers=final_headers)


def new_job(client, user_id="ana", credits=10, **extra):
    """Cria usuário e job com sucesso; devolve o corpo do job (status processing)."""
    make_user(client, user_id, credits)
    response = create_job(client, user_id=user_id, **extra)
    assert response.status_code == 201, response.text
    return response.json()
