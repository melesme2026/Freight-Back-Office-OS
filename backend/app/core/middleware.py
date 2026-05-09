from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.constants import REQUEST_ID_HEADER


PROCESS_TIME_HEADER = "X-Process-Time-Ms"


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        started_at = time.perf_counter()

        request.state.request_id = request_id
        request.state.started_at = started_at

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        started_at = getattr(request.state, "started_at", None)
        if not isinstance(started_at, (int, float)):
            started_at = time.perf_counter()
            request.state.started_at = started_at

        response = await call_next(request)

        duration_ms = (time.perf_counter() - started_at) * 1000
        response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}"
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Apply conservative cache rules to API responses.

    Private/auth/document/billing/webhook routes are explicitly no-store. Health and
    OpenAPI docs can use tiny public TTLs. Static asset caching is handled by the
    frontend/CDN config, not this API middleware.
    """

    PRIVATE_PREFIXES = (
        "/api/v1/auth",
        "/api/v1/documents",
        "/api/v1/driver/documents",
        "/api/v1/portal",
        "/api/v1/billing",
        "/api/v1/subscriptions",
        "/api/v1/payments",
        "/api/v1/webhooks",
    )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path == "/health" or path.endswith("/health"):
            response.headers.setdefault("Cache-Control", "public, max-age=15")
        elif path in {"/openapi.json", "/docs", "/redoc"}:
            response.headers.setdefault("Cache-Control", "public, max-age=300")
        elif path.startswith(self.PRIVATE_PREFIXES):
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["Pragma"] = "no-cache"
        else:
            response.headers.setdefault("Cache-Control", "no-store")
        return response
