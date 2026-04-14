"""Application configuration via environment variables and .env file."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env" if os.path.exists(".env") else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # PostgreSQL (must be set via .env or environment variable)
    database_url: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery — falls back to redis_url when not explicitly set
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @property
    def effective_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    # FPL API
    fpl_api_base_url: str = "https://fantasy.premierleague.com/api"

    # Internal API URL (for cache warming from Celery worker)
    internal_api_url: str = "http://localhost:8000"

    # Sentry
    sentry_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
