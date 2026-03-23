from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.service_plan import ServicePlan
from app.repositories.service_plan_repo import ServicePlanRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.post("/service-plans", response_model=ApiResponse)
def create_service_plan(
    *,
    organization_id: str,
    name: str,
    code: str,
    billing_cycle: str,
    base_price: str,
    description: str | None = None,
    currency_code: str = "USD",
    per_load_price: str | None = None,
    per_driver_price: str | None = None,
    is_active: bool = True,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid organization_id",
            details={"organization_id": organization_id},
        ) from exc

    repo = ServicePlanRepository(db)

    existing = repo.get_by_code(
        organization_id=parsed_organization_id,
        code=code,
    )
    if existing is not None:
        raise ValidationError(
            "Service plan code already exists for organization",
            details={"organization_id": organization_id, "code": code},
        )

    item = ServicePlan(
        organization_id=parsed_organization_id,
        name=name.strip(),
        code=code.strip(),
        description=description,
        billing_cycle=billing_cycle,
        base_price=Decimal(base_price),
        currency_code=currency_code,
        per_load_price=Decimal(per_load_price) if per_load_price is not None else None,
        per_driver_price=Decimal(per_driver_price) if per_driver_price is not None else None,
        is_active=is_active,
    )
    created = repo.create(item)

    return ApiResponse(
        data={
            "id": str(created.id),
            "organization_id": str(created.organization_id),
            "name": created.name,
            "code": created.code,
            "description": created.description,
            "billing_cycle": str(created.billing_cycle),
            "base_price": format(created.base_price, "f"),
            "currency_code": created.currency_code,
            "per_load_price": format(created.per_load_price, "f") if created.per_load_price is not None else None,
            "per_driver_price": format(created.per_driver_price, "f") if created.per_driver_price is not None else None,
            "is_active": created.is_active,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/service-plans", response_model=ApiResponse)
def list_service_plans(
    *,
    organization_id: str | None = None,
    billing_cycle: str | None = None,
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

    repo = ServicePlanRepository(db)
    items, total = repo.list(
        organization_id=parsed_organization_id,
        billing_cycle=billing_cycle,
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
                "name": item.name,
                "code": item.code,
                "description": item.description,
                "billing_cycle": str(item.billing_cycle),
                "base_price": format(item.base_price, "f"),
                "currency_code": item.currency_code,
                "per_load_price": format(item.per_load_price, "f") if item.per_load_price is not None else None,
                "per_driver_price": format(item.per_driver_price, "f") if item.per_driver_price is not None else None,
                "is_active": item.is_active,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/service-plans/{service_plan_id}", response_model=ApiResponse)
def get_service_plan(
    service_plan_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_service_plan_id = uuid.UUID(service_plan_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid service_plan_id",
            details={"service_plan_id": service_plan_id},
        ) from exc

    repo = ServicePlanRepository(db)
    item = repo.get_by_id(parsed_service_plan_id)
    if item is None:
        raise NotFoundError(
            "Service plan not found",
            details={"service_plan_id": service_plan_id},
        )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "name": item.name,
            "code": item.code,
            "description": item.description,
            "billing_cycle": str(item.billing_cycle),
            "base_price": format(item.base_price, "f"),
            "currency_code": item.currency_code,
            "per_load_price": format(item.per_load_price, "f") if item.per_load_price is not None else None,
            "per_driver_price": format(item.per_driver_price, "f") if item.per_driver_price is not None else None,
            "is_active": item.is_active,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/service-plans/{service_plan_id}", response_model=ApiResponse)
def update_service_plan(
    service_plan_id: str,
    *,
    name: str | None = None,
    code: str | None = None,
    description: str | None = None,
    billing_cycle: str | None = None,
    base_price: str | None = None,
    currency_code: str | None = None,
    per_load_price: str | None = None,
    per_driver_price: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_service_plan_id = uuid.UUID(service_plan_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid service_plan_id",
            details={"service_plan_id": service_plan_id},
        ) from exc

    repo = ServicePlanRepository(db)
    item = repo.get_by_id(parsed_service_plan_id)
    if item is None:
        raise NotFoundError(
            "Service plan not found",
            details={"service_plan_id": service_plan_id},
        )

    if code is not None and code != item.code:
        existing = repo.get_by_code(
            organization_id=item.organization_id,
            code=code,
        )
        if existing is not None and str(existing.id) != str(item.id):
            raise ValidationError(
                "Service plan code already exists for organization",
                details={"organization_id": str(item.organization_id), "code": code},
            )

    if name is not None:
        item.name = name.strip()
    if code is not None:
        item.code = code.strip()
    if description is not None:
        item.description = description
    if billing_cycle is not None:
        item.billing_cycle = billing_cycle
    if base_price is not None:
        item.base_price = Decimal(base_price)
    if currency_code is not None:
        item.currency_code = currency_code
    if per_load_price is not None:
        item.per_load_price = Decimal(per_load_price)
    if per_driver_price is not None:
        item.per_driver_price = Decimal(per_driver_price)
    if is_active is not None:
        item.is_active = is_active

    updated = repo.update(item)

    return ApiResponse(
        data={
            "id": str(updated.id),
            "organization_id": str(updated.organization_id),
            "name": updated.name,
            "code": updated.code,
            "description": updated.description,
            "billing_cycle": str(updated.billing_cycle),
            "base_price": format(updated.base_price, "f"),
            "currency_code": updated.currency_code,
            "per_load_price": format(updated.per_load_price, "f") if updated.per_load_price is not None else None,
            "per_driver_price": format(updated.per_driver_price, "f") if updated.per_driver_price is not None else None,
            "is_active": updated.is_active,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )