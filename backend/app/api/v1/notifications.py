from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.notifications.notification_service import NotificationService


router = APIRouter()


@router.post("/notifications", response_model=ApiResponse)
def create_notification(
    *,
    organization_id: str,
    channel: str,
    direction: str,
    message_type: str,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    created_by_staff_user_id: str | None = None,
    subject: str | None = None,
    body_text: str | None = None,
    provider_message_id: str | None = None,
    status: str = "queued",
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if load_id:
            uuid.UUID(load_id)
        if created_by_staff_user_id:
            uuid.UUID(created_by_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
                "created_by_staff_user_id": created_by_staff_user_id,
            },
        ) from exc

    service = NotificationService(db)
    item = service.create_notification(
        organization_id=organization_id,
        channel=channel,
        direction=direction,
        message_type=message_type,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        created_by_staff_user_id=created_by_staff_user_id,
        subject=subject,
        body_text=body_text,
        provider_message_id=provider_message_id,
        status=status,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "created_by_staff_user_id": str(item.created_by_staff_user_id) if item.created_by_staff_user_id else None,
            "channel": str(item.channel),
            "direction": item.direction,
            "message_type": item.message_type,
            "subject": item.subject,
            "body_text": item.body_text,
            "provider_message_id": item.provider_message_id,
            "status": str(item.status),
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
            "failed_at": item.failed_at.isoformat() if item.failed_at else None,
            "error_message": item.error_message,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/notifications", response_model=ApiResponse)
def list_notifications(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if load_id:
            uuid.UUID(load_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
            },
        ) from exc

    service = NotificationService(db)
    items, total = service.list_notifications(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        channel=channel,
        status=status,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
                "driver_id": str(item.driver_id) if item.driver_id else None,
                "load_id": str(item.load_id) if item.load_id else None,
                "created_by_staff_user_id": str(item.created_by_staff_user_id) if item.created_by_staff_user_id else None,
                "channel": str(item.channel),
                "direction": item.direction,
                "message_type": item.message_type,
                "subject": item.subject,
                "body_text": item.body_text,
                "provider_message_id": item.provider_message_id,
                "status": str(item.status),
                "sent_at": item.sent_at.isoformat() if item.sent_at else None,
                "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
                "failed_at": item.failed_at.isoformat() if item.failed_at else None,
                "error_message": item.error_message,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/notifications/{notification_id}", response_model=ApiResponse)
def get_notification(
    notification_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(notification_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid notification_id",
            details={"notification_id": notification_id},
        ) from exc

    service = NotificationService(db)
    item = service.get_notification(notification_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "created_by_staff_user_id": str(item.created_by_staff_user_id) if item.created_by_staff_user_id else None,
            "channel": str(item.channel),
            "direction": item.direction,
            "message_type": item.message_type,
            "subject": item.subject,
            "body_text": item.body_text,
            "provider_message_id": item.provider_message_id,
            "status": str(item.status),
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
            "failed_at": item.failed_at.isoformat() if item.failed_at else None,
            "error_message": item.error_message,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/notifications/{notification_id}/mark-sent", response_model=ApiResponse)
def mark_notification_sent(
    notification_id: str,
    *,
    provider_message_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(notification_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid notification_id",
            details={"notification_id": notification_id},
        ) from exc

    service = NotificationService(db)
    item = service.mark_sent(
        notification_id=notification_id,
        provider_message_id=provider_message_id,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "provider_message_id": item.provider_message_id,
            "sent_at": item.sent_at.isoformat() if item.sent_at else None,
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )