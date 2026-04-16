from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.notifications.notification_service import NotificationService


router = APIRouter()


class NotificationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    channel: str
    direction: str
    message_type: str
    customer_account_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    load_id: uuid.UUID | None = None
    created_by_staff_user_id: uuid.UUID | None = None
    subject: str | None = None
    body_text: str | None = None
    provider_message_id: str | None = None
    status: str = "queued"


class NotificationMarkSentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_message_id: str | None = None


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _get_token_org_id(token_payload: dict[str, Any]) -> str:
    token_org_id = token_payload.get("organization_id")
    if not token_org_id:
        raise UnauthorizedError("Token organization_id is missing")
    return str(token_org_id)


def _get_token_role(token_payload: dict[str, Any]) -> str:
    return str(token_payload.get("role") or "").strip().lower()


def _get_token_driver_id(token_payload: dict[str, Any]) -> str | None:
    token_driver_id = token_payload.get("driver_id")
    if token_driver_id is None:
        return None
    normalized = str(token_driver_id).strip()
    return normalized or None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _serialize_notification(item: Any) -> dict[str, Any]:
    recipient = item.driver_id or item.customer_account_id or item.load_id

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
        "channel": _enum_to_string(item.channel),
        "direction": item.direction,
        "message_type": item.message_type,
        "subject": item.subject,
        "recipient": str(recipient) if recipient else None,
        "body_text": item.body_text,
        "provider_message_id": item.provider_message_id,
        "status": _enum_to_string(item.status),
        "sent_at": _to_iso_or_none(item.sent_at),
        "delivered_at": _to_iso_or_none(item.delivered_at),
        "failed_at": _to_iso_or_none(item.failed_at),
        "error_message": item.error_message,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/notifications", response_model=ApiResponse)
def create_notification(
    payload: NotificationCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    if str(payload.organization_id) != token_org_id:
        raise UnauthorizedError("organization_id does not match authenticated organization")

    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_driver_id = _uuid_to_str(payload.driver_id)
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if effective_driver_id is not None and effective_driver_id != token_driver_id:
            raise UnauthorizedError("Driver may only create notifications for own driver_id")
        effective_driver_id = token_driver_id

    service = NotificationService(db)
    item = service.create_notification(
        organization_id=token_org_id,
        channel=_normalize_required_text(payload.channel, field_name="channel"),
        direction=_normalize_required_text(payload.direction, field_name="direction"),
        message_type=_normalize_required_text(payload.message_type, field_name="message_type"),
        customer_account_id=_uuid_to_str(payload.customer_account_id),
        driver_id=effective_driver_id,
        load_id=_uuid_to_str(payload.load_id),
        created_by_staff_user_id=_uuid_to_str(payload.created_by_staff_user_id),
        subject=_normalize_optional_text(payload.subject),
        body_text=_normalize_optional_text(payload.body_text),
        provider_message_id=_normalize_optional_text(payload.provider_message_id),
        status=_normalize_required_text(payload.status, field_name="status"),
    )

    db.commit()

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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    if organization_id is not None and str(organization_id) != token_org_id:
        raise UnauthorizedError("organization_id does not match authenticated organization")

    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_driver_id = _uuid_to_str(driver_id)
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if effective_driver_id is not None and effective_driver_id != token_driver_id:
            raise UnauthorizedError("Driver may only access own notifications")
        effective_driver_id = token_driver_id

    service = NotificationService(db)
    items, total = service.list_notifications(
        organization_id=token_org_id,
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=effective_driver_id,
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    service = NotificationService(db)
    item = service.get_notification(str(notification_id), organization_id=token_org_id)

    return ApiResponse(
        data=_serialize_notification(item),
        meta={},
        error=None,
    )


@router.post("/notifications/{notification_id}/mark-sent", response_model=ApiResponse)
def mark_notification_sent(
    notification_id: uuid.UUID,
    payload: NotificationMarkSentRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    service = NotificationService(db)
    item = service.mark_sent(
        notification_id=str(notification_id),
        organization_id=token_org_id,
        provider_message_id=_normalize_optional_text(payload.provider_message_id),
    )

    db.commit()

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": _enum_to_string(item.status),
            "provider_message_id": item.provider_message_id,
            "sent_at": _to_iso_or_none(item.sent_at),
            "updated_at": _to_iso_or_none(item.updated_at),
        },
        meta={},
        error=None,
    )
