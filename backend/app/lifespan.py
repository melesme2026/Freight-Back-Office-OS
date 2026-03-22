from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    configure_logging()
    settings.ensure_runtime_directories()

    logger.info(
        "Application startup complete",
        extra={
            "environment": settings.environment,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
        },
    )

    try:
        yield
    finally:
        logger.info(
            "Application shutdown complete",
            extra={
                "environment": settings.environment,
                "app_name": settings.app_name,
                "app_version": settings.app_version,
            },
        )