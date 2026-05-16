from __future__ import annotations

import pytest
import yaml
from app.core.config import ROOT_DIR, Settings, get_settings

RENDER_LAUNCH_SECRET_KEY = "render-launch-secret-key-for-production-tests"
RENDER_LAUNCH_DATABASE_URL = "sqlite+pysqlite:///:memory:"


def _backend_render_env() -> dict[str, str]:
    render_config = yaml.safe_load((ROOT_DIR / "render.yaml").read_text())
    backend_service = next(
        service
        for service in render_config["services"]
        if service["name"] == "fbos-api"
    )

    values: dict[str, str] = {}
    for env_var in backend_service["envVars"]:
        if "value" in env_var:
            values[env_var["key"]] = str(env_var["value"])

    values["SECRET_KEY"] = RENDER_LAUNCH_SECRET_KEY
    values["DATABASE_URL_OVERRIDE"] = RENDER_LAUNCH_DATABASE_URL
    return values


def test_render_launch_production_settings_validate(monkeypatch) -> None:
    for key, value in _backend_render_env().items():
        monkeypatch.setenv(key, value)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.web_app_base_url == "https://app.adwafreight.com"
    assert settings.frontend_api_url == "https://app.adwafreight.com"
    assert settings.public_backend_url == "https://app.adwafreight.com/api"
    assert "https://app.adwafreight.com" in settings.cors_allowed_origins
    assert settings.document_upload_extraction_enabled is False

    get_settings.cache_clear()


def test_production_settings_error_names_missing_launch_url_env_vars() -> None:
    settings = Settings(
        environment="production",
        debug=False,
        secret_key=RENDER_LAUNCH_SECRET_KEY,
        database_url_override=RENDER_LAUNCH_DATABASE_URL,
        web_app_base_url="https://app.adwafreight.com",
        frontend_api_url=None,
        public_backend_url=None,
    )

    with pytest.raises(ValueError, match="FRONTEND_API_URL.*PUBLIC_BACKEND_URL"):
        settings.validate_runtime_configuration()


def test_production_settings_error_names_invalid_launch_url_env_vars() -> None:
    settings = Settings(
        environment="production",
        debug=False,
        secret_key=RENDER_LAUNCH_SECRET_KEY,
        database_url_override=RENDER_LAUNCH_DATABASE_URL,
        web_app_base_url="https://app.adwafreight.com",
        frontend_api_url="app.adwafreight.com",
        public_backend_url="/api",
    )

    with pytest.raises(ValueError, match="FRONTEND_API_URL.*PUBLIC_BACKEND_URL"):
        settings.validate_runtime_configuration()


def test_default_local_settings_still_validate() -> None:
    settings = Settings(
        environment="local",
        web_app_base_url="http://localhost:3000",
        _env_file=None,
    )

    settings.validate_runtime_configuration()

    assert settings.environment == "local"
    assert settings.web_app_base_url == "http://localhost:3000"
