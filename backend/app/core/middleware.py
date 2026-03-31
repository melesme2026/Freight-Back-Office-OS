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
        if started_at is None:
            started_at = time.perf_counter()
            request.state.started_at = started_at

        response = await call_next(request)

        duration_ms = (time.perf_counter() - started_at) * 1000
        response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}"
        return response