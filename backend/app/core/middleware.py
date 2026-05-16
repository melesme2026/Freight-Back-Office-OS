from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable

from app.core.config import get_settings
from app.core.constants import REQUEST_ID_HEADER
from app.core.request_context import client_ip
from app.core.request_metrics import (
    get_request_metrics,
    reset_request_metrics,
    start_request_metrics,
)
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

        metrics_token = start_request_metrics()
        serialization_started_at: float | None = None
        response: Response | None = None
        try:
            response = await call_next(request)
            serialization_started_at = time.perf_counter()
            return response
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            metrics = get_request_metrics()
            logger.exception(
                "API endpoint failed",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status": 500,
                    "duration_ms": round(duration_ms, 2),
                    "db_query_time_ms": (
                        round(metrics.db_query_time_ms, 2) if metrics else 0.0
                    ),
                    "query_count": metrics.query_count if metrics else 0,
                    "request_id": getattr(request.state, "request_id", None),
                    "organization_id": request.headers.get("x-organization-id"),
                    "failure_reason": "unhandled_exception",
                },
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            metrics = get_request_metrics()
            status_code = response.status_code if response is not None else 500
            serialization_ms = (
                max((time.perf_counter() - serialization_started_at) * 1000, 0.0)
                if serialization_started_at is not None
                else 0.0
            )
            if response is not None:
                response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}"
                response.headers["Server-Timing"] = (
                    f"db;dur={metrics.db_query_time_ms:.2f}, "
                    f"serialize;dur={serialization_ms:.2f}, total;dur={duration_ms:.2f}"
                    if metrics is not None
                    else f"total;dur={duration_ms:.2f}"
                )
                response.headers["X-Query-Count"] = str(
                    metrics.query_count if metrics else 0
                )
            log_extra = {
                "endpoint": request.url.path,
                "path": request.url.path,
                "method": request.method,
                "status": status_code,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "db_query_time_ms": (
                    round(metrics.db_query_time_ms, 2) if metrics else 0.0
                ),
                "serialization_time_ms": round(serialization_ms, 2),
                "query_count": metrics.query_count if metrics else 0,
                "request_id": getattr(request.state, "request_id", None),
                "organization_id": request.headers.get("x-organization-id"),
                "limiter_bucket": getattr(request.state, "limiter_bucket", None),
            }
            if (
                (metrics and metrics.query_count >= 20)
                or duration_ms >= SLOW_ENDPOINT_LOG_THRESHOLD_MS
                or status_code >= 500
            ):
                logger.warning(
                    "Slow, query-heavy, or failing API endpoint completed",
                    extra=log_extra,
                )
            elif request.url.path.startswith("/api/v1/"):
                logger.info("API endpoint completed", extra=log_extra)
            reset_request_metrics(metrics_token)


class RequestConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """Bound concurrent API work without letting background reads block writes.

    Load-detail hydration previously shared one "hot" bucket for documents,
    packet audit, review context, staff users, and even upload/delete routes.
    That protected workers but allowed optional background GETs to reject normal
    user actions with a load-detail-specific message.  The limiter now classifies
    requests into independent buckets so user writes have their own capacity and
    a longer acquisition window while optional panel reads fail fast and can be
    retried by the UI.
    """

    BACKGROUND_READ_MARKERS = (
        "/documents",
        "/submission-packets",
        "/payment-reconciliation",
        "/review-queue/loads/",
        "/packet-audit",
        "/staff-users",
        "/follow-ups",
        "/invoice-status",
    )
    WORKFLOW_WRITE_MARKERS = (
        "/workflow-actions",
        "/advance-status",
        "/quick-status",
        "/submission-packets",
        "/payment-reconciliation",
        "/follow-ups",
        "/review-queue",
        "/carrier-profile",
        "/customer-accounts",
        "/brokers",
        "/drivers",
        "/staff-users",
    )
    BYPASS_PREFIXES = (
        "/health",
        "/api/v1/health",
        "/api/v1/auth",
        "/openapi.json",
        "/docs",
        "/redoc",
    )
    BUCKET_CONFIG = {
        "core_reads": {"capacity": 6, "timeout_seconds": 0.25},
        "background_panel_reads": {"capacity": 2, "timeout_seconds": 0.05},
        "document_writes": {"capacity": 6, "timeout_seconds": 1.0},
        "invoice_actions": {"capacity": 4, "timeout_seconds": 1.0},
        "workflow_status_mutations": {"capacity": 6, "timeout_seconds": 1.0},
    }
    _semaphores: dict[str, asyncio.Semaphore] = {}

    def _bucket_for_request(self, request: Request) -> str | None:
        path = request.url.path
        method = request.method.upper()
        if method == "OPTIONS" or not path.startswith("/api/v1/"):
            return None
        if path.startswith(self.BYPASS_PREFIXES):
            return None

        is_document_upload = (
            "/documents/upload" in path
            or "/driver/documents/upload" in path
            or ("/portal/" in path and "/documents/upload" in path)
        )
        if is_document_upload:
            return "document_writes"
        if method == "GET" and "/documents/" in path and path.endswith("/download"):
            return "document_writes"
        if "/documents/" in path and method in {"POST", "PATCH", "PUT", "DELETE"}:
            return "document_writes"
        if "/invoice" in path and "/invoice-status" not in path:
            return "invoice_actions"
        if method in {"POST", "PATCH", "PUT", "DELETE"} and any(
            marker in path for marker in self.WORKFLOW_WRITE_MARKERS
        ):
            return "workflow_status_mutations"
        if method == "GET" and any(marker in path for marker in self.BACKGROUND_READ_MARKERS):
            return "background_panel_reads"
        if method == "GET" and path.startswith("/api/v1/loads/"):
            return "core_reads"
        return None

    def _semaphore_key(self, request: Request, bucket: str) -> str:
        org = request.headers.get("x-organization-id") or "unknown-org"
        ip = client_ip(request) or "unknown-ip"
        return f"{bucket}:{org}:{ip}"

    @classmethod
    def reset(cls) -> None:
        cls._semaphores.clear()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        bucket = self._bucket_for_request(request)
        if bucket is None:
            return await call_next(request)

        config = self.BUCKET_CONFIG[bucket]
        key = self._semaphore_key(request, bucket)
        semaphore = self._semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(int(config["capacity"]))
            self._semaphores[key] = semaphore

        limiter_started_at = time.perf_counter()
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=float(config["timeout_seconds"]))
        except TimeoutError:
            request.state.limiter_bucket = bucket
            request.state.limiter_wait_ms = round(
                (time.perf_counter() - limiter_started_at) * 1000, 2
            )
            logger.warning(
                "API concurrency limiter rejected request",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "request_id": getattr(request.state, "request_id", None),
                    "limiter_bucket": bucket,
                    "limiter_key": key,
                    "limiter_rejection_reason": "bucket_capacity_exhausted",
                },
            )
            user_message = (
                "This optional panel is still loading. Please retry this panel shortly."
                if bucket == "background_panel_reads"
                else "This action is busy. Please try again shortly."
            )
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": "1",
                    "X-Concurrency-Limit": bucket,
                    "X-Concurrency-Rejection-Reason": "bucket_capacity_exhausted",
                },
                content={
                    "data": None,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", None),
                        "limiter_bucket": bucket,
                    },
                    "error": {
                        "code": "request_concurrency_limited",
                        "message": user_message,
                        "details": {"bucket": bucket},
                    },
                },
            )
        try:
            request.state.limiter_bucket = bucket
            request.state.limiter_wait_ms = round(
                (time.perf_counter() - limiter_started_at) * 1000, 2
            )
            response = await call_next(request)
            response.headers.setdefault("X-Concurrency-Limit", bucket)
            return response
        finally:
            semaphore.release()


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
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
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
        if path.endswith("/auth/request-password-reset") or path.endswith(
            "/auth/reset-password"
        ):
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
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Policy": policy_name,
                },
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
        response.headers.setdefault(
            "X-RateLimit-Remaining", str(max(0, max_requests - count))
        )
        response.headers.setdefault("X-RateLimit-Reset", str(int(reset_at)))
        return response
