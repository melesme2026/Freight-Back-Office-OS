from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    app_settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=app_settings.jwt_expire_minutes))

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if additional_claims:
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
) -> dict[str, Any]:
    app_settings = settings or get_settings()

    try:
        payload = jwt.decode(
            token,
            app_settings.secret_key,
            algorithms=[app_settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedError("Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Token subject is missing")

    return payload


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing bearer token")
    return credentials.credentials


def get_current_token_payload(
    token: str = Depends(get_bearer_token),
) -> dict[str, Any]:
    return decode_token(token)