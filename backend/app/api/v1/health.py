from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.healthchecks import check_database_health, check_redis_health, check_storage_health
from app.schemas.common import ApiResponse


router = APIRouter()


def _build_health_payload() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


def _email_check() -> dict[str, object]:
    settings = get_settings()
    if not settings.email_sending_enabled:
        return {"ok": True, "enabled": False, "message": "email_sending_disabled"}

    if settings.email_provider == "smtp":
        missing = [
            key
            for key, value in {
                "smtp_host": settings.smtp_host,
                "smtp_username": settings.smtp_username,
                "smtp_password": settings.smtp_password,
                "email_from_address": settings.email_from_address,
            }.items()
            if not value
        ]
        if missing:
            return {"ok": False, "enabled": True, "provider": "smtp", "message": "smtp_config_missing", "missing": missing}

    return {"ok": True, "enabled": True, "provider": settings.email_provider, "message": "configured"}


def _build_readiness_payload() -> tuple[dict[str, object], bool]:
    settings = get_settings()

    checks = {
        "app": {"ok": True, "message": "running"},
        "database": check_database_health(),
        "storage": check_storage_health(),
        "redis": check_redis_health(),
        "migrations": {"ok": True, "message": "not_checked"},
        "email": _email_check(),
    }

    is_ready = all(bool(item.get("ok")) for item in checks.values())

    payload = {
        "status": "ok" if is_ready else "degraded",
        "checks": checks,
        "environment": settings.environment,
        "service": settings.app_name,
        "version": settings.app_version,
    }
    return payload, is_ready


@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(data=_build_health_payload(), meta={}, error=None)


@router.get("/health/ready", response_model=ApiResponse)
@router.get("/health/readiness", response_model=ApiResponse)
def readiness() -> ApiResponse | JSONResponse:
    payload, is_ready = _build_readiness_payload()

    response = ApiResponse(data=payload, meta={}, error=None)

    if is_ready:
        return response

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )
