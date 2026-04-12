from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.service_plan import ServicePlan
from app.repositories.service_plan_repo import ServicePlanRepository
from app.schemas.common import ApiResponse


router = APIRouter()


class ServicePlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    name: str
    code: str
    billing_cycle: str
    base_price: str
    description: str | None = None
    currency_code: str = "USD"
    per_load_price: str | None = None
    per_driver_price: str | None = None
    is_active: bool = True


class ServicePlanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    code: str | None = None
    description: str | None = None
    billing_cycle: str | None = None
    base_price: str | None = None
    currency_code: str | None = None
    per_load_price: str | None = None
    per_driver_price: str | None = None
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


def _normalize_code(value: str) -> str:
    return _normalize_required_text(value, "code")


def _normalize_currency_code(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.upper() if normalized else None


def _parse_decimal(value: str, field_name: str) -> Decimal:
    normalized = _normalize_required_text(value, field_name)
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"Invalid {field_name}",
            details={field_name: value},
        ) from exc


def _parse_optional_decimal(value: str | None, field_name: str) -> Decimal | None:
    if value is None:
        return None
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"Invalid {field_name}",
            details={field_name: value},
        ) from exc


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _to_decimal_string(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _serialize_service_plan(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "name": item.name,
        "code": item.code,
        "description": item.description,
        "billing_cycle": _enum_to_string(item.billing_cycle),
        "base_price": _to_decimal_string(item.base_price),
        "currency_code": item.currency_code,
        "per_load_price": _to_decimal_string(item.per_load_price),
        "per_driver_price": _to_decimal_string(item.per_driver_price),
        "is_active": item.is_active,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_service_plan_or_404(
    repo: ServicePlanRepository,
    service_plan_id: uuid.UUID,
) -> ServicePlan:
    item = repo.get_by_id(service_plan_id)
    if item is None:
        raise NotFoundError(
            "Service plan not found",
            details={"service_plan_id": str(service_plan_id)},
        )
    return item


@router.post("/service-plans", response_model=ApiResponse)
def create_service_plan(
    payload: ServicePlanCreateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = ServicePlanRepository(db)

    normalized_name = _normalize_required_text(payload.name, "name")
    normalized_code = _normalize_code(payload.code)
    normalized_billing_cycle = _normalize_required_text(
        payload.billing_cycle,
        "billing_cycle",
    )
    normalized_currency_code = _normalize_currency_code(payload.currency_code) or "USD"

    existing = repo.get_by_code(
        organization_id=payload.organization_id,
        code=normalized_code,
    )
    if existing is not None:
        raise ValidationError(
            "Service plan code already exists for organization",
            details={
                "organization_id": str(payload.organization_id),
                "code": normalized_code,
            },
        )

    item = ServicePlan(
        organization_id=payload.organization_id,
        name=normalized_name,
        code=normalized_code,
        description=_normalize_optional_text(payload.description),
        billing_cycle=normalized_billing_cycle,
        base_price=_parse_decimal(payload.base_price, "base_price"),
        currency_code=normalized_currency_code,
        per_load_price=_parse_optional_decimal(payload.per_load_price, "per_load_price"),
        per_driver_price=_parse_optional_decimal(payload.per_driver_price, "per_driver_price"),
        is_active=payload.is_active,
    )
    created = repo.create(item)

    return ApiResponse(
        data=_serialize_service_plan(created),
        meta={},
        error=None,
    )


@router.get("/service-plans", response_model=ApiResponse)
def list_service_plans(
    *,
    organization_id: uuid.UUID | None = None,
    billing_cycle: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = ServicePlanRepository(db)
    items, total = repo.list(
        organization_id=organization_id,
        billing_cycle=_normalize_optional_text(billing_cycle),
        is_active=is_active,
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_service_plan(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/service-plans/{service_plan_id}", response_model=ApiResponse)
def get_service_plan(
    service_plan_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = ServicePlanRepository(db)
    item = _get_service_plan_or_404(repo, service_plan_id)

    return ApiResponse(
        data=_serialize_service_plan(item),
        meta={},
        error=None,
    )


@router.patch("/service-plans/{service_plan_id}", response_model=ApiResponse)
def update_service_plan(
    service_plan_id: uuid.UUID,
    payload: ServicePlanUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = ServicePlanRepository(db)
    item = _get_service_plan_or_404(repo, service_plan_id)

    normalized_code = _normalize_code(payload.code) if payload.code is not None else None
    if normalized_code is not None and normalized_code != item.code:
        existing = repo.get_by_code(
            organization_id=item.organization_id,
            code=normalized_code,
        )
        if existing is not None and existing.id != item.id:
            raise ValidationError(
                "Service plan code already exists for organization",
                details={
                    "organization_id": str(item.organization_id),
                    "code": normalized_code,
                },
            )

    if payload.name is not None:
        item.name = _normalize_required_text(payload.name, "name")
    if normalized_code is not None:
        item.code = normalized_code
    if payload.description is not None:
        item.description = _normalize_optional_text(payload.description)
    if payload.billing_cycle is not None:
        item.billing_cycle = _normalize_required_text(
            payload.billing_cycle,
            "billing_cycle",
        )
    if payload.base_price is not None:
        item.base_price = _parse_decimal(payload.base_price, "base_price")
    if payload.currency_code is not None:
        item.currency_code = _normalize_currency_code(payload.currency_code) or item.currency_code
    if payload.per_load_price is not None:
        item.per_load_price = _parse_optional_decimal(
            payload.per_load_price,
            "per_load_price",
        )
    if payload.per_driver_price is not None:
        item.per_driver_price = _parse_optional_decimal(
            payload.per_driver_price,
            "per_driver_price",
        )
    if payload.is_active is not None:
        item.is_active = payload.is_active

    updated = repo.update(item)

    return ApiResponse(
        data=_serialize_service_plan(updated),
        meta={},
        error=None,
    )