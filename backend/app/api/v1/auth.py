from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.dependencies import get_db_session
from app.core.exceptions import AppError, UnauthorizedError, ValidationError
from app.core.config import get_settings
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
from app.domain.models.organization import Organization
from app.domain.enums.role import Role
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.driver_repo import DriverRepository
from app.services.auth.auth_service import AuthService
from app.services.auth.token_service import TokenService
from app.services.notifications.email_service import EmailService
from app.utils.text_utils import slugify


router = APIRouter()

ACCESS_TOKEN_EXPIRES_IN_SECONDS = 60 * 60
ALLOWED_INVITE_ROLES = {role.value for role in Role}

INVITE_PERMISSION_MATRIX: dict[str, set[str]] = {
    Role.OWNER.value: ALLOWED_INVITE_ROLES,
    Role.ADMIN.value: {
        Role.OPS_AGENT.value,
        Role.BILLING_ADMIN.value,
        Role.SUPPORT_AGENT.value,
        Role.VIEWER.value,
        Role.DRIVER.value,
    },
    Role.OPS_MANAGER.value: {
        Role.OPS_AGENT.value,
        Role.SUPPORT_AGENT.value,
        Role.VIEWER.value,
        Role.DRIVER.value,
    },
}


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

    organization_id: uuid.UUID | None = None
    email: str


class ConfirmPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str


class SignupRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str
    email: str
    password: str
    confirm_password: str
    organization_name: str


def _parse_header_organization_id(x_organization_id: str | None) -> uuid.UUID | None:
    if not x_organization_id:
        return None

    try:
        return uuid.UUID(x_organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid X-Organization-Id header",
            details={"header": "X-Organization-Id", "value": x_organization_id},
        ) from exc


def _resolve_organization_id(
    *,
    payload_organization_id: uuid.UUID | None,
    x_organization_id: str | None,
) -> uuid.UUID | None:
    if payload_organization_id is not None:
        return payload_organization_id

    return _parse_header_organization_id(x_organization_id)


def _serialize_staff_user(user, *, driver_id: str | None = None) -> StaffUserAuthView:
    return StaffUserAuthView(
        id=str(user.id),
        organization_id=str(user.organization_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        driver_id=driver_id,
    )


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required", details={field_name: value})
    return normalized


def _normalize_email(value: str) -> str:
    normalized = _normalize_required_text(value, "email").lower()
    if "@" not in normalized:
        raise ValidationError("Invalid email address", details={"email": value})
    return normalized


def _normalize_role(value: str) -> str:
    normalized = _normalize_required_text(value, "role").lower()
    if normalized not in ALLOWED_INVITE_ROLES:
        raise ValidationError(
            "Invalid role",
            details={"role": value, "allowed_roles": sorted(ALLOWED_INVITE_ROLES)},
        )
    return normalized


def _build_unique_org_slug(repo: OrganizationRepository, organization_name: str) -> str:
    base_slug = slugify(organization_name) or "org"
    candidate = base_slug
    counter = 2

    while repo.get_by_slug(candidate) is not None:
        candidate = f"{base_slug}-{counter}"
        counter += 1

    return candidate


def _should_expose_auth_tokens() -> bool:
    settings = get_settings()
    return settings.email_dev_allow_token_response or settings.environment in {"local", "development", "test"}


@router.post("/auth/signup", response_model=LoginResponse)
def signup(
    payload: SignupRequestBody,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    settings = get_settings()
    if not settings.public_signup_enabled:
        raise UnauthorizedError("Public organization signup is disabled. Contact support to request workspace access.")

    normalized_full_name = _normalize_required_text(payload.full_name, "full_name")
    normalized_email = _normalize_email(payload.email)
    normalized_org_name = _normalize_required_text(payload.organization_name, "organization_name")

    if payload.password != payload.confirm_password:
        raise ValidationError("Passwords do not match", details={"field": "confirm_password"})
    if len(payload.password.strip()) < 8:
        raise ValidationError("Password must be at least 8 characters", details={"field": "password"})

    existing_email = db.scalar(select(StaffUser).where(StaffUser.email == normalized_email))
    if existing_email is not None:
        raise ValidationError("An account with this email already exists", details={"email": normalized_email})

    organization_repo = OrganizationRepository(db)
    organization = Organization(
        name=normalized_org_name,
        slug=_build_unique_org_slug(organization_repo, normalized_org_name),
        legal_name=normalized_org_name,
        email=normalized_email,
        timezone="America/Toronto",
        currency_code="USD",
        is_active=True,
        billing_provider="none",
        billing_status="trial",
        plan_code="none",
    )
    organization = organization_repo.create(organization)

    user_repo = StaffUserRepository(db)
    user = StaffUser(
        organization_id=organization.id,
        email=normalized_email,
        full_name=normalized_full_name,
        password_hash=hash_password(payload.password),
        role=Role.OWNER.value,
        is_active=True,
        last_login_at=None,
    )
    user = user_repo.create(user)

    db.commit()
    db.refresh(organization)
    db.refresh(user)

    auth_service = AuthService(db)
    access_token = auth_service.build_access_token(user)
    data = LoginResponseData(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRES_IN_SECONDS,
        user=_serialize_staff_user(user),
    )

    return LoginResponse(data=data, meta={"signup_completed": True}, error=None)


@router.post("/auth/login", response_model=LoginResponse)
def login(
    payload: LoginRequestBody,
    db: Session = Depends(get_db_session),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> LoginResponse:
    hinted_organization_id = _resolve_organization_id(
        payload_organization_id=payload.organization_id,
        x_organization_id=x_organization_id,
    )

    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate_user_for_login(
        email=payload.email,
        password=payload.password,
        organization_id=hinted_organization_id,
    )
    except AppError as exc:
        if exc.code == "multiple_organizations":
            return JSONResponse(
                status_code=422,
                content={
                    "error": "multiple_organizations",
                    "message": "This email is linked to multiple workspaces.",
                    "organizations": exc.details.get("organizations", []),
                },
            )
        raise
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
    payload = token_service.decode_access_token(token)
    user = token_service.get_current_staff_user(token)

    if user is None:
        raise UnauthorizedError("Unable to resolve current user")

    return CurrentUserResponse(
        data=_serialize_staff_user(user, driver_id=str(payload.get("driver_id")).strip() if payload.get("driver_id") else None),
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
    if requester_role not in INVITE_PERMISSION_MATRIX:
        raise UnauthorizedError("Only organization admins/managers can invite users")

    organization_id = payload.organization_id or requester.organization_id
    if str(organization_id) != str(requester.organization_id):
        raise UnauthorizedError("Cannot invite users for another organization")

    repo = StaffUserRepository(db)
    normalized_email = payload.email.strip().lower()
    normalized_full_name = _normalize_required_text(payload.full_name, "full_name")
    normalized_role = _normalize_role(payload.role)

    allowed_target_roles = INVITE_PERMISSION_MATRIX.get(requester_role, set())
    if normalized_role not in allowed_target_roles:
        raise UnauthorizedError("Your role cannot invite users for the requested target role")

    if normalized_role == Role.DRIVER.value:
        driver_repo = DriverRepository(db)
        driver_profile = driver_repo.get_by_email(
            organization_id=organization_id,
            email=normalized_email,
        )
        if driver_profile is None:
            raise ValidationError(
                "Driver profile not found for invite email. Create the driver profile first.",
                details={"email": normalized_email, "organization_id": str(organization_id)},
            )

    existing = repo.get_by_email(organization_id=organization_id, email=normalized_email)
    created_new_user = False

    if existing is None:
        item = StaffUser(
            organization_id=organization_id,
            email=normalized_email,
            full_name=normalized_full_name,
            password_hash=hash_password("ChangeMe123!"),
            role=normalized_role,
            is_active=False,
            last_login_at=None,
        )
        existing = repo.create(item)
        created_new_user = True
    else:
        existing_role = str(getattr(existing.role, "value", existing.role)).lower()
        if existing_role != normalized_role:
            raise ValidationError(
                "An account with this email already exists with a different role",
                details={
                    "email": normalized_email,
                    "existing_role": existing_role,
                    "requested_role": normalized_role,
                },
            )
        if str(existing.organization_id) != str(organization_id):
            raise UnauthorizedError("Cannot invite users for another organization")

    if created_new_user:
        db.commit()
        db.refresh(existing)

    activation_token = create_action_token(
        str(existing.id),
        token_type="activation",
        additional_claims={"organization_id": str(existing.organization_id)},
        expires_delta=timedelta(hours=24),
    )

    settings = get_settings()
    activation_url = f"{settings.web_app_base_url.rstrip('/')}/activate-account?token={activation_token}"
    email_service = EmailService()
    email_status = "unknown"
    invite_message = "Invite generated."
    email_error_message: str | None = None

    try:
        email_result = email_service.send_message(
            to_email=normalized_email,
            subject="Freight Back Office OS — Account Activation",
            body_text=(
                f"Hello {normalized_full_name},\n\n"
                "You have been invited to Freight Back Office OS.\n"
                f"Activate your account using this link:\n{activation_url}\n\n"
                "If you did not expect this invite, contact your dispatcher/admin."
            ),
            metadata={"type": "auth_invite", "organization_id": str(organization_id)},
        )
        email_status = str(email_result.get("status", "unknown"))
        invite_message = "Invite generated and email delivery was attempted."
    except ValidationError as exc:
        if str(exc) != "Email delivery is disabled in this environment":
            raise
        email_status = "disabled"
        invite_message = "Email delivery is disabled. Copy the activation link and send it manually."
        email_error_message = str(exc)

    response_data: dict[str, str | bool] = {
        "user_id": str(existing.id),
        "invite_sent": True,
        "email_status": email_status,
        "message": invite_message,
    }
    if email_error_message:
        response_data["email_error"] = email_error_message
    if _should_expose_auth_tokens() or email_status == "disabled":
        response_data["activation_url"] = activation_url
        response_data["activation_token"] = activation_token

    return ApiResponse(
        data=response_data,
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

    token_organization_id = token_payload.get("organization_id")
    if str(token_organization_id) != str(user.organization_id):
        raise UnauthorizedError("Activation token organization does not match user organization")

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
    normalized_email = payload.email.strip().lower()
    organization_id = payload.organization_id

    if organization_id is None:
        stmt = select(StaffUser.organization_id).where(StaffUser.email == normalized_email).distinct()
        organization_ids = list(db.scalars(stmt).all())
        if len(organization_ids) != 1:
            return ApiResponse(data={"reset_requested": True}, meta={}, error=None)
        organization_id = organization_ids[0]

    repo = StaffUserRepository(db)
    user = repo.get_by_email(
        organization_id=organization_id,
        email=normalized_email,
    )

    if user is None:
        return ApiResponse(data={"reset_requested": True}, meta={}, error=None)

    reset_token = create_action_token(
        str(user.id),
        token_type="password_reset",
        additional_claims={"organization_id": str(user.organization_id)},
        expires_delta=timedelta(minutes=30),
    )

    settings = get_settings()
    reset_url = f"{settings.web_app_base_url.rstrip('/')}/reset-password?token={reset_token}"
    email_service = EmailService()
    email_result = email_service.send_message(
        to_email=user.email,
        subject="Freight Back Office OS — Password Reset",
        body_text=(
            "A password reset was requested for your Freight Back Office OS account.\n\n"
            f"Reset your password using this link:\n{reset_url}\n\n"
            "If you did not request this, ignore this message."
        ),
        metadata={"type": "auth_password_reset", "organization_id": str(user.organization_id)},
    )

    response_data: dict[str, str | bool] = {
        "reset_requested": True,
        "email_status": str(email_result.get("status", "unknown")),
    }
    if _should_expose_auth_tokens():
        response_data["reset_url"] = reset_url
        response_data["reset_token"] = reset_token

    return ApiResponse(
        data=response_data,
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

    token_organization_id = token_payload.get("organization_id")
    if str(token_organization_id) != str(user.organization_id):
        raise UnauthorizedError("Reset token organization does not match user organization")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(data={"password_reset": True, "user_id": str(user.id)}, meta={}, error=None)
