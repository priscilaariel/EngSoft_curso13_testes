import sqlite3

from app.provider import ProviderClient, ProviderError, ProviderInvalidResponse
from app.repository import Repository

COSTS = {512: 1, 1024: 2, 2048: 4}


class InternalFailure(ProviderError):
    """Falha interna depois do aceite do Provedor; reaproveita o formato de erro da criação."""

    code = "internal_error"
    http_status = 500


class JobCreationFailed(Exception):
    def __init__(self, error: ProviderError, job_id: str):
        super().__init__(error.code)
        self.error = error
        self.job_id = job_id


class JobService:
    def __init__(self, repo: Repository, provider: ProviderClient):
        self.repo = repo
        self.provider = provider

    def create_job(self, user_id: str, prompt: str, resolution: int) -> dict:
        job = self.repo.create_job_debiting(user_id, prompt, resolution, COSTS[resolution])
        try:
            provider_id = self.provider.submit(job_id=job["id"], prompt=prompt, resolution=resolution)
            self._register_provider_id(job["id"], provider_id)
        except ProviderError as error:
            self.repo.fail_and_refund(job["id"], error.code)
            raise JobCreationFailed(error, job["id"])
        except sqlite3.Error:
            # o Provedor já aceitou o pedido, mas não conseguimos registrar o id: sem esse id
            # nunca receberemos o webhook, então o job é encerrado e o crédito devolvido
            error = InternalFailure()
            self.repo.fail_and_refund(job["id"], error.code)
            raise JobCreationFailed(error, job["id"])
        return self.repo.get_job(job["id"])

    def _register_provider_id(self, job_id: str, provider_id: str) -> None:
        try:
            self.repo.mark_processing(job_id, provider_id)
        except sqlite3.IntegrityError:
            # o Provedor devolveu um id que já pertence a outro job
            raise ProviderInvalidResponse()
