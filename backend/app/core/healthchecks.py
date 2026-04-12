from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import tempfile

from app.core.config import get_settings
from app.core.database import check_database_connection


def check_database_health() -> dict[str, Any]:
    db_ok, db_message = check_database_connection()
    return {
        "ok": db_ok,
        "message": db_message,
    }


def check_storage_health() -> dict[str, Any]:
    settings = get_settings()

    try:
        settings.ensure_runtime_directories()

        if settings.storage_provider == "local":
            storage_path = settings.storage_local_root_path
            path_exists = storage_path.exists()
            is_dir = storage_path.is_dir()

            if not (path_exists and is_dir):
                return {
                    "ok": False,
                    "message": "storage_path_invalid",
                    "provider": settings.storage_provider,
                    "path": str(storage_path),
                }

            # 🔥 A+++ improvement: write test (real readiness)
            try:
                test_file = Path(storage_path) / f".healthcheck_{tempfile.mkstemp()[1]}"
                test_file.write_text("healthcheck")
                test_file.unlink(missing_ok=True)
                writable = True
            except Exception:
                writable = False

            return {
                "ok": writable,
                "message": "ok" if writable else "not_writable",
                "provider": settings.storage_provider,
                "path": str(storage_path),
            }

        return {
            "ok": True,
            "message": "remote_storage_configured",
            "provider": settings.storage_provider,
            "path": None,
        }

    except Exception as exc:
        return {
            "ok": False,
            "message": str(exc),
            "provider": getattr(settings, "storage_provider", None),
            "path": None,
        }


def check_redis_health() -> dict[str, Any]:
    settings = get_settings()

    redis_url = settings.redis_url_override or settings.redis_url
    if not redis_url:
        return {
            "ok": True,
            "message": "not_configured",
            "url": None,
        }

    try:
        parsed = urlparse(redis_url)

        if parsed.scheme not in {"redis", "rediss"}:
            return {
                "ok": False,
                "message": "invalid_redis_scheme",
                "url": redis_url,
            }

        if not parsed.hostname:
            return {
                "ok": False,
                "message": "missing_redis_host",
                "url": redis_url,
            }

        # 🔥 A+++ improvement: actual connection check (lazy import, no hard dependency)
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(redis_url, socket_timeout=2)
            client.ping()

            return {
                "ok": True,
                "message": "connected",
                "url": redis_url,
                "host": parsed.hostname,
                "port": parsed.port or 6379,
                "db": parsed.path.lstrip("/") or str(settings.redis_db),
            }

        except Exception as redis_exc:
            return {
                "ok": False,
                "message": f"connection_failed: {redis_exc}",
                "url": redis_url,
                "host": parsed.hostname,
                "port": parsed.port or 6379,
            }

    except Exception as exc:
        return {
            "ok": False,
            "message": str(exc),
            "url": redis_url,
        }


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

    database = check_database_health()
    storage = check_storage_health()
    redis = check_redis_health()

    overall_ready = bool(database["ok"] and storage["ok"] and redis["ok"])

    return {
        "status": "ready" if overall_ready else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": {
            "database": database,
            "storage": storage,
            "redis": redis,
        },
    }