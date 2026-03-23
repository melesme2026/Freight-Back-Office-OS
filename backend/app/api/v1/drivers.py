from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.driver import Driver
from app.repositories.driver_repo import DriverRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.post("/drivers", response_model=ApiResponse)
def create_driver(
    *,
    organization_id: str,
    full_name: str,
    phone: str,
    customer_account_id: str | None = None,
    email: str | None = None,
    is_active: bool = True,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id)
        parsed_customer_account_id = (
            uuid.UUID(customer_account_id) if customer_account_id else None
        )
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    repo = DriverRepository(db)

    item = Driver(
        organization_id=parsed_organization_id,
        customer_account_id=parsed_customer_account_id,
        full_name=full_name.strip(),
        phone=phone.strip(),
        email=email.strip().lower() if email else None,
        is_active=is_active,
    )
    created = repo.create(item)

    return ApiResponse(
        data={
            "id": str(created.id),
            "organization_id": str(created.organization_id),
            "customer_account_id": str(created.customer_account_id) if created.customer_account_id else None,
            "full_name": created.full_name,
            "phone": created.phone,
            "email": created.email,
            "is_active": created.is_active,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/drivers", response_model=ApiResponse)
def list_drivers(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id) if organization_id else None
        parsed_customer_account_id = (
            uuid.UUID(customer_account_id) if customer_account_id else None
        )
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    repo = DriverRepository(db)
    items, total = repo.list(
        organization_id=parsed_organization_id,
        customer_account_id=parsed_customer_account_id,
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
                "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
                "full_name": item.full_name,
                "phone": item.phone,
                "email": item.email,
                "is_active": item.is_active,
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


@router.get("/drivers/{driver_id}", response_model=ApiResponse)
def get_driver(
    driver_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_driver_id = uuid.UUID(driver_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid driver_id",
            details={"driver_id": driver_id},
        ) from exc

    repo = DriverRepository(db)
    item = repo.get_by_id(parsed_driver_id)
    if item is None:
        raise NotFoundError(
            "Driver not found",
            details={"driver_id": driver_id},
        )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "full_name": item.full_name,
            "phone": item.phone,
            "email": item.email,
            "is_active": item.is_active,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/drivers/{driver_id}", response_model=ApiResponse)
def update_driver(
    driver_id: str,
    *,
    customer_account_id: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_driver_id = uuid.UUID(driver_id)
        parsed_customer_account_id = (
            uuid.UUID(customer_account_id) if customer_account_id else None
        )
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "driver_id": driver_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    repo = DriverRepository(db)
    item = repo.get_by_id(parsed_driver_id)
    if item is None:
        raise NotFoundError(
            "Driver not found",
            details={"driver_id": driver_id},
        )

    if customer_account_id is not None:
        item.customer_account_id = parsed_customer_account_id
    if full_name is not None:
        item.full_name = full_name.strip()
    if phone is not None:
        item.phone = phone.strip()
    if email is not None:
        item.email = email.strip().lower() if email else None
    if is_active is not None:
        item.is_active = is_active

    updated = repo.update(item)

    return ApiResponse(
        data={
            "id": str(updated.id),
            "organization_id": str(updated.organization_id),
            "customer_account_id": str(updated.customer_account_id) if updated.customer_account_id else None,
            "full_name": updated.full_name,
            "phone": updated.phone,
            "email": updated.email,
            "is_active": updated.is_active,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )