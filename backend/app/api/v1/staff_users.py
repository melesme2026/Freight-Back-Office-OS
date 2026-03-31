from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository
from app.schemas.common import ApiResponse


router = APIRouter()


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
        "role": str(item.role),
        "is_active": item.is_active,
        "last_login_at": _to_iso_or_none(item.last_login_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_staff_user_or_404(
    repo: StaffUserRepository,
    staff_user_id: uuid.UUID,
) -> StaffUser:
    item = repo.get_by_id(staff_user_id)
    if item is None:
        raise NotFoundError(
            "Staff user not found",
            details={"staff_user_id": str(staff_user_id)},
        )
    return item


@router.post("/staff-users", response_model=ApiResponse)
def create_staff_user(
    *,
    organization_id: uuid.UUID,
    email: str,
    full_name: str,
    password: str,
    role: str = "ops_agent",
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)

    normalized_email = _normalize_email(email)
    normalized_full_name = _normalize_required_text(full_name, "full_name")
    normalized_password = _normalize_required_text(password, "password")
    normalized_role = _normalize_required_text(role, "role")

    existing = repo.get_by_email(
        organization_id=organization_id,
        email=normalized_email,
    )
    if existing is not None:
        raise ValidationError(
            "Staff user email already exists in organization",
            details={
                "email": normalized_email,
                "organization_id": str(organization_id),
            },
        )

    item = StaffUser(
        organization_id=organization_id,
        email=normalized_email,
        full_name=normalized_full_name,
        password_hash=hash_password(normalized_password),
        role=normalized_role,
        is_active=True,
        last_login_at=None,
    )
    created = repo.create(item)

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
    *,
    email: str | None = None,
    full_name: str | None = None,
    password: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = StaffUserRepository(db)
    item = _get_staff_user_or_404(repo, staff_user_id)

    if email is not None:
        normalized_email = _normalize_email(email)
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

    if full_name is not None:
        item.full_name = _normalize_required_text(full_name, "full_name")

    if password is not None:
        item.password_hash = hash_password(
            _normalize_required_text(password, "password")
        )

    if role is not None:
        item.role = _normalize_required_text(role, "role")

    if is_active is not None:
        item.is_active = is_active

    updated = repo.update(item)

    return ApiResponse(
        data=_serialize_staff_user(updated),
        meta={},
        error=None,
    )