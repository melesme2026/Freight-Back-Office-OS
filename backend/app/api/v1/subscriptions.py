from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.billing.subscription_service import SubscriptionService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_subscription(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "service_plan_id": str(item.service_plan_id),
        "status": str(item.status),
        "starts_at": _to_iso_or_none(item.starts_at),
        "ends_at": _to_iso_or_none(item.ends_at),
        "current_period_start": _to_iso_or_none(item.current_period_start),
        "current_period_end": _to_iso_or_none(item.current_period_end),
        "cancel_at_period_end": item.cancel_at_period_end,
        "cancelled_at": _to_iso_or_none(item.cancelled_at),
        "billing_email": item.billing_email,
        "notes": item.notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/subscriptions", response_model=ApiResponse)
def create_subscription(
    *,
    organization_id: uuid.UUID,
    customer_account_id: uuid.UUID,
    service_plan_id: uuid.UUID,
    starts_at: str,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SubscriptionService(db)
    item = service.create_subscription(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        service_plan_id=str(service_plan_id),
        starts_at=starts_at,
        billing_email=_normalize_email(billing_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_subscription(item),
        meta={},
        error=None,
    )


@router.get("/subscriptions", response_model=ApiResponse)
def list_subscriptions(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    service_plan_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SubscriptionService(db)
    items, total = service.list_subscriptions(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        service_plan_id=_uuid_to_str(service_plan_id),
        status=_normalize_optional_text(status),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_subscription(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/subscriptions/{subscription_id}", response_model=ApiResponse)
def get_subscription(
    subscription_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SubscriptionService(db)
    item = service.get_subscription(str(subscription_id))

    return ApiResponse(
        data=_serialize_subscription(item),
        meta={},
        error=None,
    )


@router.patch("/subscriptions/{subscription_id}", response_model=ApiResponse)
def update_subscription(
    subscription_id: uuid.UUID,
    *,
    status: str | None = None,
    starts_at: str | None = None,
    ends_at: str | None = None,
    current_period_start: str | None = None,
    current_period_end: str | None = None,
    cancel_at_period_end: bool | None = None,
    cancelled_at: str | None = None,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SubscriptionService(db)
    item = service.update_subscription(
        subscription_id=str(subscription_id),
        status=_normalize_optional_text(status),
        starts_at=starts_at,
        ends_at=ends_at,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        cancelled_at=cancelled_at,
        billing_email=_normalize_email(billing_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_subscription(item),
        meta={},
        error=None,
    )


@router.post("/subscriptions/{subscription_id}/cancel", response_model=ApiResponse)
def cancel_subscription(
    subscription_id: uuid.UUID,
    *,
    cancel_at_period_end: bool = True,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SubscriptionService(db)
    item = service.cancel_subscription(
        subscription_id=str(subscription_id),
        cancel_at_period_end=cancel_at_period_end,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "cancel_at_period_end": item.cancel_at_period_end,
            "cancelled_at": _to_iso_or_none(item.cancelled_at),
            "ends_at": _to_iso_or_none(item.ends_at),
            "updated_at": _to_iso_or_none(item.updated_at),
        },
        meta={},
        error=None,
    )