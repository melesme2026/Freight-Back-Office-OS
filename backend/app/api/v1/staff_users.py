from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import AppError, NotFoundError, UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.domain.enums.role import Role
from app.core.security import hash_password
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository
from app.services.audit.audit_service import AuditService
from app.services.auth.team_rbac import (
    OWNER_ADMIN_ROLES,
    TeamAction,
    assert_can_manage_team,
    assert_can_modify_staff,
    normalize_role,
)
from app.schemas.common import ApiResponse


router = APIRouter()

ALLOWED_DIRECT_CREATE_ROLES = {
    Role.OPS_AGENT.value,
    Role.BILLING_ADMIN.value,
    Role.SUPPORT_AGENT.value,
    Role.VIEWER.value,
}


def _normalize_token_organization_id(token_payload: dict[str, Any]) -> uuid.UUID:
    raw_organization_id = token_payload.get("organization_id")
    try:
        return uuid.UUID(str(raw_organization_id))
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Token organization_id is invalid") from exc


def _normalize_token_role(token_payload: dict[str, Any]) -> str:
    role_value = str(token_payload.get("role", "")).strip().lower()
    if not role_value:
        raise UnauthorizedError("Token role is missing")
    return role_value


def _require_staff_admin_role(token_payload: dict[str, Any]) -> str:
    token_role = _normalize_token_role(token_payload)
    assert_can_manage_team(token_role)
    return token_role


class StaffUserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    email: str
    full_name: str
    password: str
    role: str = "ops_agent"


class StaffUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    full_name: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class StaffUserRemoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


def _normalize_role_value(value: object | None) -> str:
    return normalize_role(value)


def _count_org_admin_owners(repo: StaffUserRepository, organization_id: uuid.UUID) -> int:
    members, _ = repo.list(
        organization_id=organization_id,
        page=1,
        page_size=2000,
        include_related=False,
    )
    return sum(
        1
        for member in members
        if _normalize_role_value(member.role) in OWNER_ADMIN_ROLES and member.is_active and member.removed_at is None
    )


def _is_final_active_owner_or_admin(repo: StaffUserRepository, organization_id: uuid.UUID, target_user_id: uuid.UUID) -> bool:
    members, _ = repo.list(
        organization_id=organization_id,
        page=1,
        page_size=2000,
        include_related=False,
    )
    active_admin_owner_ids = [
        member.id
        for member in members
        if member.removed_at is None and member.is_active and _normalize_role_value(member.role) in OWNER_ADMIN_ROLES
    ]
    return len(active_admin_owner_ids) == 1 and active_admin_owner_ids[0] == target_user_id


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_email(value: str, field_name: str = "email") -> str:
    normalized = _normalize_required_text(value, field_name).lower()
    return normalized


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_staff_user(item: Any) -> dict[str, Any]:
    removed_at = _to_iso_or_none(getattr(item, "removed_at", None))
    status = "removed" if removed_at else ("active" if item.is_active else "disabled")
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "email": item.email,
        "full_name": item.full_name,
        "role": _enum_to_string(item.role),
        "is_active": item.is_active,
        "status": status,
        "removed_at": removed_at,
        "last_login_at": _to_iso_or_none(item.last_login_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_staff_user_or_404(
    repo: StaffUserRepository,
    staff_user_id: uuid.UUID,
) -> StaffUser:
    item = repo.get_by_id(staff_user_id, include_related=True)
    if item is None:
        raise NotFoundError(
            "Staff user not found",
            details={"staff_user_id": str(staff_user_id)},
        )
    return item


@router.post("/staff-users", response_model=ApiResponse)
def create_staff_user(
    payload: StaffUserCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _require_staff_admin_role(token_payload)

    token_organization_id = _normalize_token_organization_id(token_payload)
    if payload.organization_id != token_organization_id:
        raise UnauthorizedError("organization_id does not match authenticated organization")

    repo = StaffUserRepository(db)

    normalized_email = _normalize_email(payload.email)
    normalized_full_name = _normalize_required_text(payload.full_name, "full_name")
    normalized_password = _normalize_required_text(payload.password, "password")
    normalized_role = _normalize_required_text(payload.role, "role").lower()

    if normalized_role not in ALLOWED_DIRECT_CREATE_ROLES:
        raise UnauthorizedError(
            "Direct staff creation is restricted to non-privileged office roles; use invites for other roles"
        )

    existing = repo.get_by_email(
        organization_id=payload.organization_id,
        email=normalized_email,
    )
    if existing is not None:
        raise ValidationError(
            "Staff user email already exists in organization",
            details={
                "email": normalized_email,
                "organization_id": str(payload.organization_id),
            },
        )

    item = StaffUser(
        organization_id=payload.organization_id,
        email=normalized_email,
        full_name=normalized_full_name,
        password_hash=hash_password(normalized_password),
        role=normalized_role,
        is_active=True,
        last_login_at=None,
    )
    created = repo.create(item)
    created = repo.get_by_id(created.id, include_related=True) or created

    return ApiResponse(
        data=_serialize_staff_user(created),
        meta={},
        error=None,
    )


@router.get("/staff-users", response_model=ApiResponse)
def list_staff_users(
    *,
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    include_removed: bool = False,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _require_staff_admin_role(token_payload)

    repo = StaffUserRepository(db)
    token_organization_id = _normalize_token_organization_id(token_payload)

    if organization_id is not None and organization_id != token_organization_id:
        raise UnauthorizedError("organization_id does not match authenticated organization")

    effective_organization_id = organization_id or token_organization_id
    items, total = repo.list(
        organization_id=effective_organization_id,
        role=_normalize_optional_text(role),
        is_active=is_active,
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
        include_removed=include_removed,
        include_related=True,
    )

    return ApiResponse(
        data=[_serialize_staff_user(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/staff-users/{staff_user_id}", response_model=ApiResponse)
def get_staff_user(
    staff_user_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _require_staff_admin_role(token_payload)

    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)
    token_organization_id = _normalize_token_organization_id(token_payload)
    if item.organization_id != token_organization_id:
        raise UnauthorizedError("Staff user is not in authenticated organization")

    return ApiResponse(
        data=_serialize_staff_user(item),
        meta={},
        error=None,
    )


@router.patch("/staff-users/{staff_user_id}", response_model=ApiResponse)
def update_staff_user(
    staff_user_id: uuid.UUID,
    payload: StaffUserUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_role = _require_staff_admin_role(token_payload)

    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)
    token_organization_id = _normalize_token_organization_id(token_payload)
    if item.organization_id != token_organization_id:
        raise UnauthorizedError("Staff user is not in authenticated organization")
    if item.removed_at is not None:
        raise ValidationError("Removed team members cannot be modified")
    requester_id = str(token_payload.get("sub") or "").strip()
    try:
        requester_uuid = uuid.UUID(requester_id)
    except ValueError as exc:
        raise UnauthorizedError("Token subject is invalid") from exc
    target_role = _normalize_role_value(item.role)

    if payload.email is not None:
        normalized_email = _normalize_email(payload.email)
        if normalized_email != item.email:
            existing = repo.get_by_email(
                organization_id=item.organization_id,
                email=normalized_email,
            )
            if existing is not None and existing.id != item.id:
                raise ValidationError(
                    "Staff user email already exists in organization",
                    details={
                        "email": normalized_email,
                        "organization_id": str(item.organization_id),
                    },
                )
            item.email = normalized_email

    if payload.full_name is not None:
        item.full_name = _normalize_required_text(payload.full_name, "full_name")

    if payload.password is not None:
        item.password_hash = hash_password(
            _normalize_required_text(payload.password, "password")
        )

    if payload.role is not None:
        normalized_target_role = _normalize_required_text(payload.role, "role").lower()
        if normalized_target_role == Role.OWNER.value and token_role != Role.OWNER.value:
            raise UnauthorizedError("Only owner can assign owner role")
        if normalized_target_role in {Role.ADMIN.value, Role.OPS_MANAGER.value} and token_role != Role.OWNER.value:
            raise UnauthorizedError("Only owner can assign admin or ops manager roles")
        if normalized_target_role == Role.DRIVER.value:
            raise UnauthorizedError("Driver role must be onboarded through the invite flow")
        current_role = _normalize_role_value(item.role)
        if (
            current_role in {Role.OWNER.value, Role.ADMIN.value}
            and normalized_target_role not in {Role.OWNER.value, Role.ADMIN.value}
            and _count_org_admin_owners(repo, item.organization_id) <= 1
        ):
            raise AppError(
                "At least one active owner/admin is required.",
                code="final_admin_required",
                status_code=422,
            )
        item.role = normalized_target_role

    if payload.is_active is not None:
        if payload.is_active is False:
            assert_can_modify_staff(token_role, target_role, TeamAction.DISABLE)
            if str(item.id) == requester_id and _is_final_active_owner_or_admin(repo, item.organization_id, requester_uuid):
                raise AppError(
                    "You cannot disable yourself as the final active owner/admin.",
                    code="cannot_remove_self_as_final_admin",
                    status_code=422,
                )
            if _is_final_active_owner_or_admin(repo, item.organization_id, item.id):
                raise AppError(
                    "At least one active owner/admin is required.",
                    code="final_admin_required",
                    status_code=422,
                )
        else:
            assert_can_modify_staff(token_role, target_role, TeamAction.ENABLE)
        item.is_active = payload.is_active

    updated = repo.update(item)
    updated = repo.get_by_id(updated.id, include_related=True) or updated
    action = None
    if payload.is_active is False:
        action = "staff_disabled"
    elif payload.is_active is True:
        action = "staff_enabled"
    if action:
        AuditService(db).log_event(
            organization_id=str(updated.organization_id),
            actor_type="staff_user",
            actor_id=requester_id,
            entity_type="staff_user",
            entity_id=str(updated.id),
            action=action,
            metadata_json={"role": _normalize_role_value(updated.role)},
        )

    return ApiResponse(
        data=_serialize_staff_user(updated),
        meta={},
        error=None,
    )


@router.patch("/staff-users/{staff_user_id}/remove", response_model=ApiResponse)
def remove_staff_user(
    staff_user_id: uuid.UUID,
    payload: StaffUserRemoveRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_role = _require_staff_admin_role(token_payload)
    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)
    token_organization_id = _normalize_token_organization_id(token_payload)
    if item.organization_id != token_organization_id:
        raise UnauthorizedError("Staff user is not in authenticated organization")

    requester_id = str(token_payload.get("sub") or "").strip()
    target_role = _normalize_role_value(item.role)
    assert_can_modify_staff(token_role, target_role, TeamAction.REMOVE)

    if str(item.id) == requester_id and _is_final_active_owner_or_admin(repo, item.organization_id, item.id):
        raise AppError(
            "You cannot remove yourself as the final active owner/admin.",
            code="cannot_remove_self_as_final_admin",
            status_code=422,
        )
    if _is_final_active_owner_or_admin(repo, item.organization_id, item.id):
        raise AppError(
            "At least one active owner/admin is required.",
            code="final_admin_required",
            status_code=422,
        )

    item.is_active = False
    item.removed_at = datetime.now(timezone.utc)
    updated = repo.update(item)
    AuditService(db).log_event(
        organization_id=str(updated.organization_id),
        actor_type="staff_user",
        actor_id=requester_id,
        entity_type="staff_user",
        entity_id=str(updated.id),
        action="staff_removed",
        metadata_json={"reason": _normalize_optional_text(payload.reason), "role": _normalize_role_value(updated.role)},
    )
    return ApiResponse(data={"id": str(staff_user_id), "removed": True}, meta={}, error=None)


@router.delete("/staff-users/{staff_user_id}", response_model=ApiResponse)
def delete_staff_user(
    staff_user_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    return remove_staff_user(staff_user_id, StaffUserRemoveRequest(), token_payload, db)
