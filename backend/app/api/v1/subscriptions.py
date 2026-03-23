from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.billing.subscription_service import SubscriptionService


router = APIRouter()


@router.post("/subscriptions", response_model=ApiResponse)
def create_subscription(
    *,
    organization_id: str,
    customer_account_id: str,
    service_plan_id: str,
    starts_at: str,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        uuid.UUID(customer_account_id)
        uuid.UUID(service_plan_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "service_plan_id": service_plan_id,
            },
        ) from exc

    service = SubscriptionService(db)
    item = service.create_subscription(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        service_plan_id=service_plan_id,
        starts_at=starts_at,
        billing_email=billing_email,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "service_plan_id": str(item.service_plan_id),
            "status": str(item.status),
            "starts_at": item.starts_at.isoformat() if hasattr(item.starts_at, "isoformat") else str(item.starts_at),
            "ends_at": item.ends_at.isoformat() if item.ends_at and hasattr(item.ends_at, "isoformat") else (str(item.ends_at) if item.ends_at else None),
            "current_period_start": item.current_period_start.isoformat() if hasattr(item.current_period_start, "isoformat") else str(item.current_period_start),
            "current_period_end": item.current_period_end.isoformat() if hasattr(item.current_period_end, "isoformat") else str(item.current_period_end),
            "cancel_at_period_end": item.cancel_at_period_end,
            "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at and hasattr(item.cancelled_at, "isoformat") else (str(item.cancelled_at) if item.cancelled_at else None),
            "billing_email": item.billing_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/subscriptions", response_model=ApiResponse)
def list_subscriptions(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    service_plan_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if service_plan_id:
            uuid.UUID(service_plan_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "service_plan_id": service_plan_id,
            },
        ) from exc

    service = SubscriptionService(db)
    items, total = service.list_subscriptions(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        service_plan_id=service_plan_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "service_plan_id": str(item.service_plan_id),
                "status": str(item.status),
                "starts_at": item.starts_at.isoformat() if hasattr(item.starts_at, "isoformat") else str(item.starts_at),
                "ends_at": item.ends_at.isoformat() if item.ends_at and hasattr(item.ends_at, "isoformat") else (str(item.ends_at) if item.ends_at else None),
                "current_period_start": item.current_period_start.isoformat() if hasattr(item.current_period_start, "isoformat") else str(item.current_period_start),
                "current_period_end": item.current_period_end.isoformat() if hasattr(item.current_period_end, "isoformat") else str(item.current_period_end),
                "cancel_at_period_end": item.cancel_at_period_end,
                "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at and hasattr(item.cancelled_at, "isoformat") else (str(item.cancelled_at) if item.cancelled_at else None),
                "billing_email": item.billing_email,
                "notes": item.notes,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/subscriptions/{subscription_id}", response_model=ApiResponse)
def get_subscription(
    subscription_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(subscription_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid subscription_id",
            details={"subscription_id": subscription_id},
        ) from exc

    service = SubscriptionService(db)
    item = service.get_subscription(subscription_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "service_plan_id": str(item.service_plan_id),
            "status": str(item.status),
            "starts_at": item.starts_at.isoformat() if hasattr(item.starts_at, "isoformat") else str(item.starts_at),
            "ends_at": item.ends_at.isoformat() if item.ends_at and hasattr(item.ends_at, "isoformat") else (str(item.ends_at) if item.ends_at else None),
            "current_period_start": item.current_period_start.isoformat() if hasattr(item.current_period_start, "isoformat") else str(item.current_period_start),
            "current_period_end": item.current_period_end.isoformat() if hasattr(item.current_period_end, "isoformat") else str(item.current_period_end),
            "cancel_at_period_end": item.cancel_at_period_end,
            "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at and hasattr(item.cancelled_at, "isoformat") else (str(item.cancelled_at) if item.cancelled_at else None),
            "billing_email": item.billing_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/subscriptions/{subscription_id}", response_model=ApiResponse)
def update_subscription(
    subscription_id: str,
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
    try:
        uuid.UUID(subscription_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid subscription_id",
            details={"subscription_id": subscription_id},
        ) from exc

    service = SubscriptionService(db)
    item = service.update_subscription(
        subscription_id=subscription_id,
        status=status,
        starts_at=starts_at,
        ends_at=ends_at,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        cancelled_at=cancelled_at,
        billing_email=billing_email,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "service_plan_id": str(item.service_plan_id),
            "status": str(item.status),
            "starts_at": item.starts_at.isoformat() if hasattr(item.starts_at, "isoformat") else str(item.starts_at),
            "ends_at": item.ends_at.isoformat() if item.ends_at and hasattr(item.ends_at, "isoformat") else (str(item.ends_at) if item.ends_at else None),
            "current_period_start": item.current_period_start.isoformat() if hasattr(item.current_period_start, "isoformat") else str(item.current_period_start),
            "current_period_end": item.current_period_end.isoformat() if hasattr(item.current_period_end, "isoformat") else str(item.current_period_end),
            "cancel_at_period_end": item.cancel_at_period_end,
            "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at and hasattr(item.cancelled_at, "isoformat") else (str(item.cancelled_at) if item.cancelled_at else None),
            "billing_email": item.billing_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/subscriptions/{subscription_id}/cancel", response_model=ApiResponse)
def cancel_subscription(
    subscription_id: str,
    *,
    cancel_at_period_end: bool = True,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(subscription_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid subscription_id",
            details={"subscription_id": subscription_id},
        ) from exc

    service = SubscriptionService(db)
    item = service.cancel_subscription(
        subscription_id=subscription_id,
        cancel_at_period_end=cancel_at_period_end,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "cancel_at_period_end": item.cancel_at_period_end,
            "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at and hasattr(item.cancelled_at, "isoformat") else (str(item.cancelled_at) if item.cancelled_at else None),
            "ends_at": item.ends_at.isoformat() if item.ends_at and hasattr(item.ends_at, "isoformat") else (str(item.ends_at) if item.ends_at else None),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )