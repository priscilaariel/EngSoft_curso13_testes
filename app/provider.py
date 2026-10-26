import time
from typing import Callable

import httpx

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 10


class ProviderError(Exception):
    code = "provider_error"
    http_status = 502


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"
    http_status = 502


class ProviderTimeout(ProviderError):
    code = "provider_timeout"
    http_status = 504


class ProviderRejected(ProviderError):
    code = "provider_rejected"
    http_status = 502


class ProviderInvalidResponse(ProviderError):
    code = "provider_invalid_response"
    http_status = 502


class ProviderClient:
    def __init__(
        self,
        http: httpx.Client,
        base_url: str,
        api_key: str,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def submit(self, *, job_id: str, prompt: str, resolution: int) -> str:
        """Envia o pedido de geração e devolve o id do Provedor."""
        payload = {"prompt": prompt, "size": resolution, "client_reference": job_id}
        headers = {"Authorization": f"Bearer {self.api_key}", "Idempotency-Key": job_id}
        last_error: ProviderError = ProviderUnavailable()

        for attempt in range(1, self.max_attempts + 1):
            wait = self.backoff_seconds * (2 ** (attempt - 1))
            try:
                response = self.http.post(f"{self.base_url}/v1/generations", json=payload, headers=headers)
            except httpx.TimeoutException:
                last_error = ProviderTimeout()
            except httpx.TransportError:
                last_error = ProviderUnavailable()
            else:
                if response.status_code == 202:
                    return self._parse_id(response)
                if response.status_code in RETRYABLE_STATUSES:
                    last_error = ProviderUnavailable()
                    if response.status_code == 429:
                        wait = self._retry_after(response, wait)
                elif 400 <= response.status_code < 500:
                    raise ProviderRejected()
                else:
                    raise ProviderInvalidResponse()

            if attempt < self.max_attempts:
                self.sleep(wait)

        raise last_error

    @staticmethod
    def _retry_after(response: httpx.Response, default: float) -> float:
        value = response.headers.get("Retry-After", "")
        if value.isascii() and value.isdigit():
            return min(int(value), MAX_RETRY_AFTER_SECONDS)
        return default

    @staticmethod
    def _parse_id(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            raise ProviderInvalidResponse()
        provider_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(provider_id, str) or not provider_id:
            raise ProviderInvalidResponse()
        return provider_id
