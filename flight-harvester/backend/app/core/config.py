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
    cors_origins: str = "http://localhost:5173"
    allowed_hosts: str = "localhost,127.0.0.1,test,backend,frontend"

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_list_to_string(cls, v: object) -> str:
        if isinstance(v, list):
            import json
            return json.dumps(v)
        return str(v)

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, v: str) -> str:
        for origin in cls._parse_csv_or_json(v):
            if origin == "*":
                raise ValueError(
                    "CORS_ORIGINS cannot contain '*'. Specify explicit origins like "
                    "'https://app.example.com' to prevent credentialed-request abuse."
                )
        return v

    @staticmethod
    def _parse_csv_or_json(raw: str) -> list[str]:
        v = raw.strip()
        if v.startswith("["):
            import json
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            return [str(x).strip() for x in parsed if str(x).strip()]
        return [item.strip() for item in v.split(",") if item.strip()]

    def get_cors_origins(self) -> list[str]:
        return self._parse_csv_or_json(self.cors_origins)

    def get_allowed_hosts(self) -> list[str]:
        return self._parse_csv_or_json(self.allowed_hosts)
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
        ssl = parse_qs(parsed.query).get("ssl", [""])[0]
        if host and host not in _LOCAL_DB_HOSTS and ssl != "require":
            raise ValueError(
                "Remote PostgreSQL connections must include ssl=require in DATABASE_URL"
            )
        return v


    @field_validator("debug", "scheduler_enabled", "expose_api_docs", mode="before")
    @classmethod
    def parse_bool(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "release", "production")
        return bool(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
