from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.notifications.notification_service import NotificationService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str) -> str:
    return value.strip()


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_notification(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": (
            str(item.customer_account_id) if item.customer_account_id else None
        ),
        "driver_id": str(item.driver_id) if item.driver_id else None,
        "load_id": str(item.load_id) if item.load_id else None,
        "created_by_staff_user_id": (
            str(item.created_by_staff_user_id)
            if item.created_by_staff_user_id
            else None
        ),
        "channel": str(item.channel),
        "direction": item.direction,
        "message_type": item.message_type,
        "subject": item.subject,
        "body_text": item.body_text,
        "provider_message_id": item.provider_message_id,
        "status": str(item.status),
        "sent_at": _to_iso_or_none(item.sent_at),
        "delivered_at": _to_iso_or_none(item.delivered_at),
        "failed_at": _to_iso_or_none(item.failed_at),
        "error_message": item.error_message,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/notifications", response_model=ApiResponse)
def create_notification(
    *,
    organization_id: uuid.UUID,
    channel: str,
    direction: str,
    message_type: str,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    created_by_staff_user_id: uuid.UUID | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    provider_message_id: str | None = None,
    status: str = "queued",
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = NotificationService(db)
    item = service.create_notification(
        organization_id=str(organization_id),
        channel=_normalize_required_text(channel),
        direction=_normalize_required_text(direction),
        message_type=_normalize_required_text(message_type),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        created_by_staff_user_id=_uuid_to_str(created_by_staff_user_id),
        subject=_normalize_optional_text(subject),
        body_text=body_text,
        provider_message_id=_normalize_optional_text(provider_message_id),
        status=_normalize_required_text(status),
    )

    return ApiResponse(
        data=_serialize_notification(item),
        meta={},
        error=None,
    )


@router.get("/notifications", response_model=ApiResponse)
def list_notifications(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    channel: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = NotificationService(db)
    items, total = service.list_notifications(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        channel=_normalize_optional_text(channel),
        status=_normalize_optional_text(status),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_notification(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/notifications/{notification_id}", response_model=ApiResponse)
def get_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = NotificationService(db)
    item = service.get_notification(str(notification_id))

    return ApiResponse(
        data=_serialize_notification(item),
        meta={},
        error=None,
    )


@router.post("/notifications/{notification_id}/mark-sent", response_model=ApiResponse)
def mark_notification_sent(
    notification_id: uuid.UUID,
    *,
    provider_message_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = NotificationService(db)
    item = service.mark_sent(
        notification_id=str(notification_id),
        provider_message_id=_normalize_optional_text(provider_message_id),
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "provider_message_id": item.provider_message_id,
            "sent_at": _to_iso_or_none(item.sent_at),
            "updated_at": _to_iso_or_none(item.updated_at),
        },
        meta={},
        error=None,
    )