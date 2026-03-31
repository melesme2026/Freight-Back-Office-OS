from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.healthchecks import (
    check_database_health,
    check_redis_health,
    check_storage_health,
)
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


def _build_readiness_payload() -> tuple[dict[str, object], bool]:
    settings = get_settings()

    database = check_database_health()
    storage = check_storage_health()
    redis = check_redis_health()

    is_ready = all([database["ok"], storage["ok"], redis["ok"]])

    payload = {
        "status": "ok" if is_ready else "degraded",
        "database": database,
        "storage": storage,
        "redis": redis,
        "environment": settings.environment,
        "service": settings.app_name,
        "version": settings.app_version,
    }
    return payload, is_ready


@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(
        data=_build_health_payload(),
        meta={},
        error=None,
    )


@router.get("/health/ready", response_model=ApiResponse)
def readiness() -> ApiResponse | JSONResponse:
    payload, is_ready = _build_readiness_payload()

    response = ApiResponse(
        data=payload,
        meta={},
        error=None,
    )

    if is_ready:
        return response

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )