from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.post("/staff-users", response_model=ApiResponse)
def create_staff_user(
    *,
    organization_id: str,
    email: str,
    full_name: str,
    password: str,
    role: str = "ops_agent",
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid organization_id",
            details={"organization_id": organization_id},
        ) from exc

    repo = StaffUserRepository(db)

    existing = repo.get_by_email(
        organization_id=parsed_organization_id,
        email=email.strip().lower(),
    )
    if existing is not None:
        raise ValidationError(
            "Staff user email already exists in organization",
            details={"email": email, "organization_id": organization_id},
        )

    item = StaffUser(
        organization_id=parsed_organization_id,
        email=email.strip().lower(),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        last_login_at=None,
    )
    created = repo.create(item)

    return ApiResponse(
        data={
            "id": str(created.id),
            "organization_id": str(created.organization_id),
            "email": created.email,
            "full_name": created.full_name,
            "role": str(created.role),
            "is_active": created.is_active,
            "last_login_at": created.last_login_at.isoformat() if created.last_login_at else None,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/staff-users", response_model=ApiResponse)
def list_staff_users(
    *,
    organization_id: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    parsed_organization_id = None
    if organization_id:
        try:
            parsed_organization_id = uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    repo = StaffUserRepository(db)
    items, total = repo.list(
        organization_id=parsed_organization_id,
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "email": item.email,
                "full_name": item.full_name,
                "role": str(item.role),
                "is_active": item.is_active,
                "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/staff-users/{staff_user_id}", response_model=ApiResponse)
def get_staff_user(
    staff_user_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_staff_user_id = uuid.UUID(staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid staff_user_id",
            details={"staff_user_id": staff_user_id},
        ) from exc

    repo = StaffUserRepository(db)
    item = repo.get_by_id(parsed_staff_user_id)
    if item is None:
        raise NotFoundError(
            "Staff user not found",
            details={"staff_user_id": staff_user_id},
        )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "email": item.email,
            "full_name": item.full_name,
            "role": str(item.role),
            "is_active": item.is_active,
            "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/staff-users/{staff_user_id}", response_model=ApiResponse)
def update_staff_user(
    staff_user_id: str,
    *,
    email: str | None = None,
    full_name: str | None = None,
    password: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_staff_user_id = uuid.UUID(staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid staff_user_id",
            details={"staff_user_id": staff_user_id},
        ) from exc

    repo = StaffUserRepository(db)
    item = repo.get_by_id(parsed_staff_user_id)
    if item is None:
        raise NotFoundError(
            "Staff user not found",
            details={"staff_user_id": staff_user_id},
        )

    if email and email.strip().lower() != item.email:
        existing = repo.get_by_email(
            organization_id=item.organization_id,
            email=email.strip().lower(),
        )
        if existing is not None and str(existing.id) != str(item.id):
            raise ValidationError(
                "Staff user email already exists in organization",
                details={"email": email, "organization_id": str(item.organization_id)},
            )
        item.email = email.strip().lower()

    if full_name is not None:
        item.full_name = full_name.strip()

    if password is not None:
        item.password_hash = hash_password(password)

    if role is not None:
        item.role = role

    if is_active is not None:
        item.is_active = is_active

    updated = repo.update(item)

    return ApiResponse(
        data={
            "id": str(updated.id),
            "organization_id": str(updated.organization_id),
            "email": updated.email,
            "full_name": updated.full_name,
            "role": str(updated.role),
            "is_active": updated.is_active,
            "last_login_at": updated.last_login_at.isoformat() if updated.last_login_at else None,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )