from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_db_session
from app.core.healthchecks import (
    check_database_health,
    check_redis_health,
    check_storage_health,
)
from app.schemas.common import ApiResponse


router = APIRouter()


@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    settings = get_settings()

    return ApiResponse(
        data={
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        meta={},
        error=None,
    )


@router.get("/health/ready", response_model=ApiResponse)
def readiness(
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    settings = get_settings()

    database_ok, database_message = check_database_health(db)
    storage_ok, storage_message = check_storage_health()
    redis_ok, redis_message = check_redis_health()

    overall_status = "ok" if all([database_ok, storage_ok, redis_ok]) else "degraded"

    return ApiResponse(
        data={
            "status": overall_status,
            "database": {
                "ok": database_ok,
                "message": database_message,
            },
            "storage": {
                "ok": storage_ok,
                "message": storage_message,
            },
            "redis": {
                "ok": redis_ok,
                "message": redis_message,
            },
            "environment": settings.environment,
        },
        meta={},
        error=None,
    )