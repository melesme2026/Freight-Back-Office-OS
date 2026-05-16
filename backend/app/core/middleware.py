from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from app.core.config import get_settings
from app.core.constants import REQUEST_ID_HEADER
from app.core.request_context import client_ip
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

PROCESS_TIME_HEADER = "X-Process-Time-Ms"
SLOW_ENDPOINT_LOG_THRESHOLD_MS = 1500
logger = logging.getLogger(__name__)


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
        if duration_ms >= SLOW_ENDPOINT_LOG_THRESHOLD_MS:
            logger.warning(
                "Slow API endpoint completed",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative browser security headers without blocking app flows."""

    CSP = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com; "
        "connect-src 'self' https://api.stripe.com https://checkout.stripe.com; "
        "frame-src https://js.stripe.com https://checkout.stripe.com"
    )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response = await call_next(request)
        settings = get_settings()
        if not settings.security_headers_enabled:
            return response
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers.setdefault("Content-Security-Policy", self.CSP)
        if settings.environment == "production" and settings.security_hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory fixed-window limiter for abuse-prone public/sensitive endpoints.

    The limiter is intentionally conservative and skips Stripe/webhook routes so
    provider retries are not blocked by per-instance counters. Deployments can
    layer Redis/CDN limits later without changing endpoint behavior.
    """

    _buckets: dict[str, tuple[int, float]] = {}

    def _policy_for_path(self, path: str) -> tuple[str, int, int] | None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return None
        if "/webhook" in path or "/webhooks" in path:
            return None
        if path.endswith("/auth/login"):
            return (
                "auth_login",
                settings.rate_limit_login_max_requests,
                settings.rate_limit_login_window_seconds,
            )
        if path.endswith("/auth/request-password-reset") or path.endswith("/auth/reset-password"):
            return (
                "password_reset",
                settings.rate_limit_login_max_requests,
                settings.rate_limit_login_window_seconds,
            )
        if path.endswith("/demo-requests"):
            return (
                "demo_requests",
                settings.rate_limit_public_max_requests,
                settings.rate_limit_public_window_seconds,
            )
        if path.endswith("/billing/checkout-session"):
            return (
                "billing_checkout",
                settings.rate_limit_billing_max_requests,
                settings.rate_limit_billing_window_seconds,
            )
        if "/portal/" in path:
            if path.endswith("/documents/upload"):
                return (
                    "portal_upload",
                    settings.rate_limit_upload_max_requests,
                    settings.rate_limit_upload_window_seconds,
                )
            return (
                "portal",
                settings.rate_limit_public_max_requests,
                settings.rate_limit_public_window_seconds,
            )
        if path.endswith("/documents") or "/documents/upload" in path:
            return (
                "document_upload",
                settings.rate_limit_upload_max_requests,
                settings.rate_limit_upload_window_seconds,
            )
        return None

    @classmethod
    def reset(cls) -> None:
        cls._buckets.clear()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        policy = self._policy_for_path(request.url.path)
        if policy is None or request.method.upper() == "OPTIONS":
            return await call_next(request)

        policy_name, max_requests, window_seconds = policy
        ip = client_ip(request) or "unknown"
        actor_hint = (
            request.headers.get("authorization", "")[-16:]
            if request.headers.get("authorization")
            else "anonymous"
        )
        key = f"{policy_name}:{ip}:{actor_hint}"
        now = time.time()
        count, reset_at = self._buckets.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        self._buckets[key] = (count, reset_at)
        retry_after = max(1, int(reset_at - now))

        if count > max_requests:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after), "X-RateLimit-Policy": policy_name},
                content={
                    "data": None,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", None),
                        "retry_after_seconds": retry_after,
                    },
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please wait and try again.",
                        "details": {
                            "policy": policy_name,
                            "limit": max_requests,
                            "window_seconds": window_seconds,
                        },
                    },
                },
            )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(max_requests))
        response.headers.setdefault("X-RateLimit-Remaining", str(max(0, max_requests - count)))
        response.headers.setdefault("X-RateLimit-Reset", str(int(reset_at)))
        return response
