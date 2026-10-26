import os
from dataclasses import dataclass


@dataclass
class Settings:
    db_path: str = "render_jobs.db"
    provider_base_url: str = "https://provider.example"
    provider_api_key: str = "dev-key"
    webhook_secret: str = "dev-secret"
    provider_max_attempts: int = 3
    provider_backoff_seconds: float = 0.5
    provider_timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            db_path=os.getenv("RJ_DB_PATH", defaults.db_path),
            provider_base_url=os.getenv("RJ_PROVIDER_URL", defaults.provider_base_url),
            provider_api_key=os.getenv("RJ_PROVIDER_KEY", defaults.provider_api_key),
            webhook_secret=os.getenv("RJ_WEBHOOK_SECRET", defaults.webhook_secret),
        )
