from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import (
    create_action_token,
    decode_token,
    get_bearer_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import (
    CurrentUserResponse,
    LoginResponse,
    LoginResponseData,
    StaffUserAuthView,
)
from app.schemas.common import ApiResponse
from app.repositories.staff_user_repo import StaffUserRepository
from app.domain.models.staff_user import StaffUser
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService


router = APIRouter()

ACCESS_TOKEN_EXPIRES_IN_SECONDS = 60 * 60


class LoginRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    organization_id: uuid.UUID | None = None




class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str




class InviteUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    full_name: str
    role: str
    organization_id: uuid.UUID | None = None


class ActivateAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    password: str


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    email: str


class ConfirmPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str
def _resolve_organization_id(
    *,
    payload_organization_id: uuid.UUID | None,
    x_organization_id: str | None,
) -> uuid.UUID:
    if payload_organization_id is not None:
        return payload_organization_id

    if not x_organization_id:
        raise ValidationError(
            "Missing organization_id. Provide X-Organization-Id header or organization_id in request body.",
            details={
                "header": "X-Organization-Id",
                "field": "organization_id",
            },
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
    payload: LoginRequestBody,
    db: Session = Depends(get_db_session),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> LoginResponse:
    organization_id = _resolve_organization_id(
        payload_organization_id=payload.organization_id,
        x_organization_id=x_organization_id,
    )

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


@router.post("/auth/change-password", response_model=ApiResponse)
def change_password(
    payload: ChangePasswordRequest,
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_service = TokenService(db)
    user = token_service.get_current_staff_user(token)

    if not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(
        data={"id": str(user.id), "password_updated": True},
        meta={},
        error=None,
    )


@router.post("/auth/invite-user", response_model=ApiResponse)
def invite_user(
    payload: InviteUserRequest,
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_service = TokenService(db)
    requester = token_service.get_current_staff_user(token)

    requester_role = str(getattr(requester.role, "value", requester.role)).lower()
    if requester_role not in {"owner", "admin", "ops_manager"}:
        raise UnauthorizedError("Only organization admins/managers can invite users")

    organization_id = payload.organization_id or requester.organization_id
    if str(organization_id) != str(requester.organization_id):
        raise UnauthorizedError("Cannot invite users for another organization")

    repo = StaffUserRepository(db)
    normalized_email = payload.email.strip().lower()
    existing = repo.get_by_email(organization_id=organization_id, email=normalized_email)

    if existing is None:
        item = StaffUser(
            organization_id=organization_id,
            email=normalized_email,
            full_name=payload.full_name.strip(),
            password_hash=hash_password("ChangeMe123!"),
            role=payload.role.strip().lower(),
            is_active=False,
            last_login_at=None,
        )
        existing = repo.create(item)

    activation_token = create_action_token(
        str(existing.id),
        token_type="activation",
        additional_claims={"organization_id": str(existing.organization_id)},
        expires_delta=timedelta(hours=24),
    )

    return ApiResponse(
        data={"user_id": str(existing.id), "activation_token": activation_token},
        meta={},
        error=None,
    )


@router.post("/auth/activate-account", response_model=ApiResponse)
def activate_account(
    payload: ActivateAccountRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_payload = decode_token(payload.token, expected_token_type="activation")
    user_id = token_payload.get("sub")

    token_service = TokenService(db)
    user = token_service.staff_user_repo.get_by_id(user_id, include_related=True)
    if user is None:
        raise UnauthorizedError("Invalid activation token")

    user.password_hash = hash_password(payload.password)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(data={"activated": True, "user_id": str(user.id)}, meta={}, error=None)


@router.post("/auth/request-password-reset", response_model=ApiResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)
    user = repo.get_by_email(
        organization_id=payload.organization_id,
        email=payload.email.strip().lower(),
    )

    if user is None:
        return ApiResponse(data={"reset_requested": True}, meta={}, error=None)

    reset_token = create_action_token(
        str(user.id),
        token_type="password_reset",
        additional_claims={"organization_id": str(user.organization_id)},
        expires_delta=timedelta(minutes=30),
    )

    return ApiResponse(
        data={"reset_requested": True, "reset_token": reset_token},
        meta={},
        error=None,
    )


@router.post("/auth/reset-password", response_model=ApiResponse)
def reset_password(
    payload: ConfirmPasswordResetRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_payload = decode_token(payload.token, expected_token_type="password_reset")
    user_id = token_payload.get("sub")

    token_service = TokenService(db)
    user = token_service.staff_user_repo.get_by_id(user_id, include_related=True)
    if user is None:
        raise UnauthorizedError("Invalid reset token")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(data={"password_reset": True, "user_id": str(user.id)}, meta={}, error=None)
