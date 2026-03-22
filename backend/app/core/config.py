from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = ROOT_DIR / "docs"
INFRA_DIR = ROOT_DIR / "infra"
SHARED_DIR = ROOT_DIR / "shared"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Freight Back Office OS API")
    app_version: str = Field(default="0.1.0")
    environment: Literal["local", "development", "staging", "production"] = Field(
        default="local"
    )
    debug: bool = Field(default=True)
    secret_key: str = Field(
        default="change-me-in-real-environments",
        min_length=16,
    )
    api_v1_prefix: str = Field(default="/api/v1")

    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="freight_back_office_os")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    sqlalchemy_echo: bool = Field(default=False)
    sqlalchemy_pool_pre_ping: bool = Field(default=True)
    sqlalchemy_pool_size: int = Field(default=10, ge=1)
    sqlalchemy_max_overflow: int = Field(default=20, ge=0)

    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0, ge=0)
    redis_password: str | None = Field(default=None)

    celery_broker_url: str | None = Field(default=None)
    celery_result_backend: str | None = Field(default=None)

    storage_provider: Literal["local", "s3", "minio"] = Field(default="local")
    storage_bucket_name: str = Field(default="freight-back-office-os")
    storage_local_root: str = Field(default="data/sandbox/uploaded-docs")
    storage_endpoint_url: str | None = Field(default=None)
    storage_access_key: str | None = Field(default=None)
    storage_secret_key: str | None = Field(default=None)
    storage_region: str | None = Field(default=None)
    storage_use_ssl: bool = Field(default=False)

    sentry_dsn: str | None = Field(default=None)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_json: bool = Field(default=True)

    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60, ge=1)

    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4.1-mini")
    ai_enabled: bool = Field(default=False)

    whatsapp_enabled: bool = Field(default=False)
    whatsapp_provider: Literal["twilio", "meta", "none"] = Field(default="none")
    whatsapp_verify_token: str | None = Field(default=None)
    whatsapp_webhook_secret: str | None = Field(default=None)

    email_enabled: bool = Field(default=False)
    email_provider: Literal["smtp", "ses", "sendgrid", "none"] = Field(default="none")
    default_from_email: str = Field(default="no-reply@freightbackoffice.local")

    billing_enabled: bool = Field(default=False)
    payment_provider: Literal["stripe", "manual", "none"] = Field(default="none")
    stripe_secret_key: str | None = Field(default=None)
    stripe_webhook_secret: str | None = Field(default=None)

    healthcheck_timeout_seconds: int = Field(default=5, ge=1)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_allowed_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("cors_allowed_origins must be a list[str] or comma-separated str")

    @field_validator("cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def _parse_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("Expected a list[str] or comma-separated str")

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        return value.lower()

    @computed_field
    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @computed_field
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @computed_field
    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field
    @property
    def effective_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @computed_field
    @property
    def effective_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @computed_field
    @property
    def storage_local_root_path(self) -> Path:
        return ROOT_DIR / self.storage_local_root

    @computed_field
    @property
    def docs_path(self) -> Path:
        return DOCS_DIR

    @computed_field
    @property
    def data_path(self) -> Path:
        return DATA_DIR

    @computed_field
    @property
    def backend_path(self) -> Path:
        return BACKEND_DIR

    @computed_field
    @property
    def app_path(self) -> Path:
        return APP_DIR

    def ensure_runtime_directories(self) -> None:
        self.storage_local_root_path.mkdir(parents=True, exist_ok=True)

    def validate_runtime_configuration(self) -> None:
        if self.is_production:
            if self.secret_key == "change-me-in-real-environments":
                raise ValueError("secret_key must be changed in production")
            if self.debug:
                raise ValueError("debug must be False in production")
            if self.storage_provider in {"s3", "minio"}:
                if not self.storage_access_key or not self.storage_secret_key:
                    raise ValueError(
                        "storage_access_key and storage_secret_key are required "
                        "when using s3/minio in production"
                    )
            if self.whatsapp_enabled and self.whatsapp_provider == "none":
                raise ValueError("whatsapp_provider must be configured when whatsapp_enabled=True")
            if self.billing_enabled and self.payment_provider == "none":
                raise ValueError("payment_provider must be configured when billing_enabled=True")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_directories()
    settings.validate_runtime_configuration()
    return settings
