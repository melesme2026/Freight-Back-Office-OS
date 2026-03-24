from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.database import check_database_connection


def get_basic_health_status() -> dict[str, Any]:
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


def get_readiness_status() -> dict[str, Any]:
    settings = get_settings()

    db_ok, db_message = check_database_connection()

    storage_ok = True
    storage_message = "ok"
    try:
        settings.ensure_runtime_directories()
    except Exception as exc:
        storage_ok = False
        storage_message = str(exc)

    redis_ok = True
    redis_message = "not_checked_yet"

    overall_ready = db_ok and storage_ok and redis_ok

    return {
        "status": "ready" if overall_ready else "not_ready",
        "database": {
            "ok": db_ok,
            "message": db_message,
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
    }
    