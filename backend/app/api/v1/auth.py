from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import get_bearer_token
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LoginResponseData,
    StaffUserAuthView,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService


router = APIRouter()

ACCESS_TOKEN_EXPIRES_IN_SECONDS = 60 * 60


def _parse_organization_header(x_organization_id: str | None) -> uuid.UUID:
    if not x_organization_id:
        raise ValidationError(
            "Missing required X-Organization-Id header",
            details={"header": "X-Organization-Id"},
        )

    try:
        return uuid.UUID(x_organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid X-Organization-Id header",
            details={"header": "X-Organization-Id", "value": x_organization_id},
        ) from exc


def _serialize_staff_user(user) -> StaffUserAuthView:
    return StaffUserAuthView(
        id=str(user.id),
        organization_id=str(user.organization_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db_session),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> LoginResponse:
    organization_id = _parse_organization_header(x_organization_id)

    auth_service = AuthService(db)
    user = auth_service.authenticate_staff_user(
        organization_id=organization_id,
        email=payload.email,
        password=payload.password,
    )
    access_token = auth_service.build_access_token(user)

    data = LoginResponseData(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRES_IN_SECONDS,
        user=_serialize_staff_user(user),
    )
    return LoginResponse(data=data, meta={}, error=None)


@router.get("/auth/me", response_model=CurrentUserResponse)
def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db_session),
) -> CurrentUserResponse:
    token_service = TokenService(db)
    user = token_service.get_current_staff_user(token)

    if user is None:
        raise UnauthorizedError("Unable to resolve current user")

    return CurrentUserResponse(
        data=_serialize_staff_user(user),
        meta={},
        error=None,
    )