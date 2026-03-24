from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import ProcessTimeMiddleware, RequestContextMiddleware
from app.lifespan import lifespan

settings = get_settings()

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(ProcessTimeMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(
        settings,
        "cors_allowed_origins",
        getattr(settings, "cors_allowed_origins_list", ["*"]),
    ),
    allow_credentials=getattr(settings, "cors_allow_credentials", True),
    allow_methods=getattr(settings, "cors_allow_methods", ["*"]),
    allow_headers=getattr(settings, "cors_allow_headers", ["*"]),
)

register_exception_handlers(app)

app.include_router(api_router)