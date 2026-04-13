from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError, ValidationError


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

_RESERVED_TOKEN_CLAIMS = {"sub", "iat", "exp", "type"}


def hash_password(password: str) -> str:
    normalized_password = password.strip()
    if not normalized_password:
        raise ValidationError(
            "Password cannot be empty",
            details={"field": "password"},
        )
    if len(normalized_password) < 8:
        raise ValidationError(
            "Password must be at least 8 characters",
            details={"field": "password"},
        )
    return password_context.hash(normalized_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    return password_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str,
    *,
    token_type: str,
    settings: Settings | None = None,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    normalized_subject = subject.strip()
    if not normalized_subject:
        raise ValidationError(
            "Token subject cannot be empty",
            details={"field": "subject"},
        )

    app_settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=app_settings.jwt_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": normalized_subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": token_type,
    }

    if additional_claims:
        conflicting_claims = sorted(
            key for key in additional_claims.keys() if key in _RESERVED_TOKEN_CLAIMS
        )
        if conflicting_claims:
            raise ValidationError(
                "additional_claims contains reserved token claims",
                details={"claims": conflicting_claims},
            )
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        app_settings.secret_key,
        algorithm=app_settings.jwt_algorithm,
    )


def decode_token(
    token: str,
    *,
    settings: Settings | None = None,
    expected_token_type: str = "access",
) -> dict[str, Any]:
    if not token or not token.strip():
        raise UnauthorizedError("Missing authentication token")

    app_settings = settings or get_settings()

    try:
        payload = jwt.decode(
            token.strip(),
            app_settings.secret_key,
            algorithms=[app_settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except JWTError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc

    token_type = payload.get("type")
    if token_type != expected_token_type:
        raise UnauthorizedError("Invalid token type")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise UnauthorizedError("Token subject is missing")

    return payload


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Invalid authentication scheme")

    token = credentials.credentials.strip() if credentials.credentials else ""
    if not token:
        raise UnauthorizedError("Missing bearer token")

    return token


def get_current_token_payload(
    token: str = Depends(get_bearer_token),
) -> dict[str, Any]:
    return decode_token(token)

def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        subject,
        token_type="access",
        settings=settings,
        additional_claims=additional_claims,
        expires_delta=expires_delta,
    )


def create_action_token(
    subject: str,
    *,
    token_type: str,
    settings: Settings | None = None,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    normalized_type = token_type.strip().lower()
    if not normalized_type:
        raise ValidationError("Token type cannot be empty", details={"field": "token_type"})

    return _create_token(
        subject,
        token_type=normalized_type,
        settings=settings,
        additional_claims=additional_claims,
        expires_delta=expires_delta,
    )
