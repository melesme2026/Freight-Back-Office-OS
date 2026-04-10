from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository
from app.schemas.common import ApiResponse


router = APIRouter()


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
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "email": item.email,
        "full_name": item.full_name,
        "role": _enum_to_string(item.role),
        "is_active": item.is_active,
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
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)

    normalized_email = _normalize_email(payload.email)
    normalized_full_name = _normalize_required_text(payload.full_name, "full_name")
    normalized_password = _normalize_required_text(payload.password, "password")
    normalized_role = _normalize_required_text(payload.role, "role")

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
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)
    items, total = repo.list(
        organization_id=organization_id,
        role=_normalize_optional_text(role),
        is_active=is_active,
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
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
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)

    return ApiResponse(
        data=_serialize_staff_user(item),
        meta={},
        error=None,
    )


@router.patch("/staff-users/{staff_user_id}", response_model=ApiResponse)
def update_staff_user(
    staff_user_id: uuid.UUID,
    payload: StaffUserUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)

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
        item.role = _normalize_required_text(payload.role, "role")

    if payload.is_active is not None:
        item.is_active = payload.is_active

    updated = repo.update(item)
    updated = repo.get_by_id(updated.id, include_related=True) or updated

    return ApiResponse(
        data=_serialize_staff_user(updated),
        meta={},
        error=None,
    )