from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = ROOT_DIR / "docs"
INFRA_DIR = ROOT_DIR / "infra"
SHARED_DIR = ROOT_DIR / "shared"

_DEFAULT_SECRET_KEY = "change-me-in-real-environments"
_ALLOWED_ENVIRONMENTS = {"local", "development", "staging", "production"}
_ALLOWED_STORAGE_PROVIDERS = {"local", "s3", "minio"}
_ALLOWED_WHATSAPP_PROVIDERS = {"twilio", "meta", "none"}
_ALLOWED_EMAIL_PROVIDERS = {"smtp", "ses", "sendgrid", "none"}
_ALLOWED_PAYMENT_PROVIDERS = {"stripe", "manual", "none"}


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
    debug: bool = Field(default=False)
    secret_key: str = Field(
        default=_DEFAULT_SECRET_KEY,
        min_length=16,
    )
    api_v1_prefix: str = Field(default="/api/v1")
    timezone: str = Field(default="UTC")

    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000, ge=1, le=65535)

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://127.0.0.1",
            "http://localhost:80",
            "http://127.0.0.1:80",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="freight_back_office_os")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    database_url_override: str | None = Field(default=None)

    sqlalchemy_echo: bool = Field(default=False)
    sqlalchemy_pool_pre_ping: bool = Field(default=True)
    sqlalchemy_pool_size: int = Field(default=10, ge=1)
    sqlalchemy_max_overflow: int = Field(default=20, ge=0)

    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0)
    redis_password: str | None = Field(default=None)
    redis_url_override: str | None = Field(default=None)

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
    web_app_base_url: str = Field(default="http://localhost:3000")
    email_dev_allow_token_response: bool = Field(default=False)
    smtp_host: str | None = Field(default=None)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = Field(default=None)
    smtp_password: str | None = Field(default=None)
    smtp_use_tls: bool = Field(default=True)
    smtp_use_ssl: bool = Field(default=False)

    billing_enabled: bool = Field(default=False)
    payment_provider: Literal["stripe", "manual", "none"] = Field(default="none")
    stripe_secret_key: str | None = Field(default=None)
    stripe_webhook_secret: str | None = Field(default=None)

    healthcheck_timeout_seconds: int = Field(default=5, ge=1)

    @field_validator(
        "debug",
        "cors_allow_credentials",
        "sqlalchemy_echo",
        "sqlalchemy_pool_pre_ping",
        "storage_use_ssl",
        "log_json",
        "ai_enabled",
        "whatsapp_enabled",
        "email_enabled",
        "email_dev_allow_token_response",
        "smtp_use_tls",
        "smtp_use_ssl",
        "billing_enabled",
        mode="before",
    )
    @classmethod
    def _parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off"}:
                return False
        if isinstance(value, int):
            return bool(value)
        raise TypeError("Expected a boolean-compatible value")

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

    @field_validator(
        "app_name",
        "app_version",
        "api_v1_prefix",
        "timezone",
        "postgres_host",
        "postgres_db",
        "postgres_user",
        "redis_host",
        "storage_bucket_name",
        "jwt_algorithm",
        "openai_model",
        "default_from_email",
        "web_app_base_url",
        mode="before",
    )
    @classmethod
    def _strip_required_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("Expected a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty")
        return normalized

    @field_validator(
        "database_url_override",
        "redis_url_override",
        "celery_broker_url",
        "celery_result_backend",
        "storage_endpoint_url",
        "storage_access_key",
        "storage_secret_key",
        "storage_region",
        "sentry_dsn",
        "openai_api_key",
        "whatsapp_verify_token",
        "whatsapp_webhook_secret",
        "stripe_secret_key",
        "stripe_webhook_secret",
        "smtp_host",
        "smtp_username",
        "smtp_password",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("Expected a string or None")
        normalized = value.strip()
        return normalized or None

    @field_validator("environment", mode="before")
    @classmethod
    def _validate_environment(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("environment must be a string")
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_ENVIRONMENTS:
            raise ValueError(f"environment must be one of {sorted(_ALLOWED_ENVIRONMENTS)}")
        return normalized

    @field_validator("storage_provider", mode="before")
    @classmethod
    def _validate_storage_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("storage_provider must be a string")
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_STORAGE_PROVIDERS:
            raise ValueError(
                f"storage_provider must be one of {sorted(_ALLOWED_STORAGE_PROVIDERS)}"
            )
        return normalized

    @field_validator("whatsapp_provider", mode="before")
    @classmethod
    def _validate_whatsapp_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("whatsapp_provider must be a string")
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_WHATSAPP_PROVIDERS:
            raise ValueError(
                f"whatsapp_provider must be one of {sorted(_ALLOWED_WHATSAPP_PROVIDERS)}"
            )
        return normalized

    @field_validator("email_provider", mode="before")
    @classmethod
    def _validate_email_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("email_provider must be a string")
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_EMAIL_PROVIDERS:
            raise ValueError(
                f"email_provider must be one of {sorted(_ALLOWED_EMAIL_PROVIDERS)}"
            )
        return normalized

    @field_validator("payment_provider", mode="before")
    @classmethod
    def _validate_payment_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("payment_provider must be a string")
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_PAYMENT_PROVIDERS:
            raise ValueError(
                f"payment_provider must be one of {sorted(_ALLOWED_PAYMENT_PROVIDERS)}"
            )
        return normalized

    @field_validator("storage_local_root")
    @classmethod
    def _validate_storage_local_root(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("storage_local_root cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def _validate_cross_field_configuration(self) -> Settings:
        if self.api_v1_prefix and not self.api_v1_prefix.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")

        if self.storage_provider == "local" and not self.storage_local_root:
            raise ValueError("storage_local_root is required when storage_provider='local'")

        if self.storage_provider in {"s3", "minio"} and not self.storage_bucket_name:
            raise ValueError(
                "storage_bucket_name is required when storage_provider is s3 or minio"
            )

        if self.whatsapp_enabled and self.whatsapp_provider == "none":
            raise ValueError(
                "whatsapp_provider must be configured when whatsapp_enabled=True"
            )

        if self.email_enabled and self.email_provider == "none":
            raise ValueError(
                "email_provider must be configured when email_enabled=True"
            )
        if self.email_enabled and self.email_provider == "smtp" and not self.smtp_host:
            raise ValueError("smtp_host must be configured when email_enabled=True and email_provider='smtp'")

        if self.billing_enabled and self.payment_provider == "none":
            raise ValueError(
                "payment_provider must be configured when billing_enabled=True"
            )

        if self.ai_enabled and not self.openai_api_key:
            raise ValueError("openai_api_key must be configured when ai_enabled=True")

        if self.payment_provider == "stripe" and self.billing_enabled and not self.stripe_secret_key:
            raise ValueError(
                "stripe_secret_key must be configured when payment_provider='stripe' and billing_enabled=True"
            )

        return self

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
        if self.database_url_override:
            return self.database_url_override

        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override

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
        root = Path(self.storage_local_root)
        return root if root.is_absolute() else (ROOT_DIR / root)

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

    @computed_field
    @property
    def infra_path(self) -> Path:
        return INFRA_DIR

    @computed_field
    @property
    def shared_path(self) -> Path:
        return SHARED_DIR

    def ensure_runtime_directories(self) -> None:
        self.data_path.mkdir(parents=True, exist_ok=True)
        if self.storage_provider == "local":
            self.storage_local_root_path.mkdir(parents=True, exist_ok=True)

    def validate_runtime_configuration(self) -> None:
        if self.is_production:
            if self.secret_key == _DEFAULT_SECRET_KEY:
                raise ValueError("secret_key must be changed in production")
            if self.debug:
                raise ValueError("debug must be False in production")

            if self.storage_provider in {"s3", "minio"}:
                if not self.storage_access_key or not self.storage_secret_key:
                    raise ValueError(
                        "storage_access_key and storage_secret_key are required "
                        "when using s3/minio in production"
                    )

            if self.whatsapp_enabled:
                if self.whatsapp_provider == "none":
                    raise ValueError(
                        "whatsapp_provider must be configured when whatsapp_enabled=True"
                    )
                if not self.whatsapp_webhook_secret:
                    raise ValueError(
                        "whatsapp_webhook_secret must be configured in production when whatsapp_enabled=True"
                    )

            if self.email_enabled and self.email_provider == "none":
                raise ValueError(
                    "email_provider must be configured when email_enabled=True"
                )

            if self.billing_enabled:
                if self.payment_provider == "none":
                    raise ValueError(
                        "payment_provider must be configured when billing_enabled=True"
                    )
                if self.payment_provider == "stripe":
                    if not self.stripe_secret_key:
                        raise ValueError(
                            "stripe_secret_key must be configured in production when using Stripe"
                        )
                    if not self.stripe_webhook_secret:
                        raise ValueError(
                            "stripe_webhook_secret must be configured in production when using Stripe"
                        )

            if self.ai_enabled and not self.openai_api_key:
                raise ValueError(
                    "openai_api_key must be configured when ai_enabled=True"
                )

            if not self.cors_allowed_origins:
                raise ValueError("cors_allowed_origins must not be empty in production")

        if not self.is_local and self.secret_key == _DEFAULT_SECRET_KEY:
            raise ValueError("secret_key must be changed outside local environment")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_directories()
    settings.validate_runtime_configuration()
    return settings
