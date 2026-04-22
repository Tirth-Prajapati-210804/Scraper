from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qs, urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "db", "postgres"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Flight Price Tracker API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "test", "backend", "frontend"]
    expose_api_docs: bool = False

    # Database
    database_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120
    admin_email: str
    admin_password: str
    admin_full_name: str = "System Admin"

    # Provider API keys (empty = disabled)
    # SerpAPI Google Flights: accurate real-time prices — sign up at serpapi.com
    serpapi_key: str = ""
    # deep_search=true mirrors exact Google Flights browser prices but is 4-6x slower (~20s/search).
    # Set SERPAPI_DEEP_SEARCH=false for faster collection at the cost of minor price variance (~5-10%).
    serpapi_deep_search: bool = True
    # Demo mode: generates realistic fake prices without any API key.
    # Set DEMO_MODE=true for demos/testing. Never use in production.
    demo_mode: bool = False
    # Scheduler
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 60
    scrape_days_ahead: int = 365
    scrape_batch_size: int = 10
    scrape_delay_seconds: float = 1.0
    provider_timeout_seconds: int = 30
    provider_max_retries: int = 3
    provider_concurrency_limit: int = 2
    provider_min_delay_seconds: float = 1.0
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    scrape_rate_limit_attempts: int = 3
    scrape_rate_limit_window_seconds: int = 300

    # Monitoring
    sentry_dsn: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters. Generate one with: openssl rand -hex 32")
        if "change-me" in v.lower() or "change_me" in v.lower():
            raise ValueError("JWT_SECRET_KEY is still set to the example value. Generate a real secret with: openssl rand -hex 32")
        return v

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("ADMIN_PASSWORD must be at least 12 characters")
        if "change-me" in v.lower() or "change_me" in v.lower():
            raise ValueError("ADMIN_PASSWORD is still set to the example value. Set a real password in .env")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme != "postgresql+asyncpg":
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg scheme")

        host = parsed.hostname or ""
        sslmode = parse_qs(parsed.query).get("sslmode", [""])[0]
        if host and host not in _LOCAL_DB_HOSTS and sslmode != "require":
            raise ValueError(
                "Remote PostgreSQL connections must include sslmode=require in DATABASE_URL"
            )
        return v

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_list_setting(cls, v: object) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlparse(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS_ORIGINS must contain explicit http(s) origins")
        return origins

    @field_validator("debug", "scheduler_enabled", "expose_api_docs", mode="before")
    @classmethod
    def parse_bool(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "release", "production")
        return bool(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
