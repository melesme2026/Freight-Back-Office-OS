from __future__ import annotations

import asyncio
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.services.audit.audit_service import AuditService
from app.services.auth.mfa_service import MfaService


def test_audit_metadata_sanitization_redacts_nested_secrets() -> None:
    sanitized = AuditService._sanitize_metadata(
        {
            "password": "do-not-store",
            "nested": {
                "portal_token": "secret-token",
                "safe": "kept",
                "raw_document_bytes": "private-bytes",
            },
            "notes": "x" * 700,
        }
    )

    assert sanitized == {
        "password": "[redacted]",
        "nested": {
            "portal_token": "[redacted]",
            "safe": "kept",
            "raw_document_bytes": "[redacted]",
        },
        "notes": "x" * 500,
    }


def test_mfa_totp_foundation_generates_uri_and_verifies_current_code() -> None:
    secret = MfaService.generate_totp_secret()
    now = int(time.time())
    code = MfaService._totp_at(secret, now // MfaService.TIME_STEP_SECONDS)

    uri = MfaService.provisioning_uri(email="Owner@Example.com", secret=secret)

    assert uri.startswith("otpauth://totp/")
    assert "secret=" in uri
    assert MfaService.verify_totp(secret=secret, code=code, at_time=now)
    assert not MfaService.verify_totp(secret=secret, code="000000", at_time=now + 180)



def _request(path: str, *, method: str = "POST", client_host: str = "203.0.113.10") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": (client_host, 12345),
            "scheme": "https",
            "server": ("testserver", 443),
            "query_string": b"",
        }
    )


async def _ok_response(_request: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


def test_rate_limit_returns_structured_429_and_skips_stripe_webhook(monkeypatch) -> None:
    RateLimitMiddleware.reset()
    monkeypatch.setenv("RATE_LIMIT_LOGIN_MAX_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "60")
    from app.core.config import get_settings

    get_settings.cache_clear()
    middleware = RateLimitMiddleware(app=lambda _scope, _receive, _send: None)

    first = asyncio.run(middleware.dispatch(_request("/api/v1/auth/login"), _ok_response))
    second = asyncio.run(middleware.dispatch(_request("/api/v1/auth/login"), _ok_response))
    limited = asyncio.run(middleware.dispatch(_request("/api/v1/auth/login"), _ok_response))

    assert first.status_code == 200
    assert second.status_code == 200
    assert limited.status_code == 429
    assert limited.headers["retry-after"]

    body = limited.body.decode("utf-8")
    assert '"code":"rate_limited"' in body
    assert '"policy":"auth_login"' in body

    for _ in range(5):
        webhook_response = asyncio.run(
            middleware.dispatch(_request("/api/v1/billing/stripe/webhook"), _ok_response)
        )
        assert webhook_response.status_code == 200

    get_settings.cache_clear()
    RateLimitMiddleware.reset()


def test_security_headers_are_present(monkeypatch) -> None:
    RateLimitMiddleware.reset()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key-for-pr48-tests")
    monkeypatch.setenv("DATABASE_URL_OVERRIDE", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("FRONTEND_API_URL", "https://app.adwafreight.com")
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://api.adwafreight.com")
    from app.core.config import get_settings

    get_settings.cache_clear()
    middleware = SecurityHeadersMiddleware(app=lambda _scope, _receive, _send: None)
    response = asyncio.run(middleware.dispatch(_request("/api/v1/auth/login"), _ok_response))

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")

    get_settings.cache_clear()
    RateLimitMiddleware.reset()
