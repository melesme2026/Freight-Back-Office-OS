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
from app.services.support.support_service import SupportService
from app.services.support.ticket_routing_service import TicketRoutingService


router = APIRouter()


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    subject: str
    description: str
    customer_account_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    load_id: uuid.UUID | None = None
    priority: str = "normal"
    assigned_to_staff_user_id: uuid.UUID | None = None


class SupportTicketUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    load_id: uuid.UUID | None = None
    subject: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to_staff_user_id: uuid.UUID | None = None
    resolved_at: str | None = None


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_required_text(value: str, *, field_name: str) -> str:
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


def _serialize_support_ticket(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id)
        if item.customer_account_id
        else None,
        "driver_id": str(item.driver_id) if item.driver_id else None,
        "load_id": str(item.load_id) if item.load_id else None,
        "assigned_to_staff_user_id": str(item.assigned_to_staff_user_id)
        if item.assigned_to_staff_user_id
        else None,
        "subject": item.subject,
        "description": item.description,
        "status": _enum_to_string(item.status),
        "priority": _enum_to_string(item.priority),
        "resolved_at": _to_iso_or_none(item.resolved_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/support/tickets", response_model=ApiResponse)
def create_support_ticket(
    payload: SupportTicketCreateRequest,
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
            raise UnauthorizedError("Driver may only create tickets for own driver_id")
        effective_driver_id = token_driver_id

    normalized_priority = _normalize_required_text(
        payload.priority,
        field_name="priority",
    )
    normalized_subject = _normalize_required_text(
        payload.subject,
        field_name="subject",
    )
    normalized_description = _normalize_required_text(
        payload.description,
        field_name="description",
    )

    routing = TicketRoutingService().route(
        priority=normalized_priority,
        customer_account_id=_uuid_to_str(payload.customer_account_id),
        load_id=_uuid_to_str(payload.load_id),
    )

    service = SupportService(db)
    item = service.create_ticket(
        organization_id=token_org_id,
        subject=normalized_subject,
        description=normalized_description,
        customer_account_id=_uuid_to_str(payload.customer_account_id),
        driver_id=effective_driver_id,
        load_id=_uuid_to_str(payload.load_id),
        priority=normalized_priority,
        assigned_to_staff_user_id=_uuid_to_str(payload.assigned_to_staff_user_id),
    )

    payload_out = _serialize_support_ticket(item)
    payload_out["route"] = routing

    return ApiResponse(
        data=payload_out,
        meta={},
        error=None,
    )


@router.get("/support/tickets", response_model=ApiResponse)
def list_support_tickets(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    assigned_to_staff_user_id: uuid.UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
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
            raise UnauthorizedError("Driver may only access own support tickets")
        effective_driver_id = token_driver_id

    service = SupportService(db)
    items, total = service.list_tickets(
        organization_id=token_org_id,
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=effective_driver_id,
        load_id=_uuid_to_str(load_id),
        assigned_to_staff_user_id=_uuid_to_str(assigned_to_staff_user_id),
        status=_normalize_optional_text(status),
        priority=_normalize_optional_text(priority),
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_support_ticket(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/support/tickets/{ticket_id}", response_model=ApiResponse)
def get_support_ticket(
    ticket_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    service = SupportService(db)
    item = service.get_ticket(str(ticket_id), organization_id=token_org_id)

    return ApiResponse(
        data=_serialize_support_ticket(item),
        meta={},
        error=None,
    )


@router.patch("/support/tickets/{ticket_id}", response_model=ApiResponse)
def update_support_ticket(
    ticket_id: uuid.UUID,
    payload: SupportTicketUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = _get_token_org_id(token_payload)
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_driver_id = _uuid_to_str(payload.driver_id)
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if effective_driver_id is not None and effective_driver_id != token_driver_id:
            raise UnauthorizedError("Driver may only update own support tickets")
        effective_driver_id = token_driver_id

    service = SupportService(db)
    item = service.update_ticket(
        ticket_id=str(ticket_id),
        organization_id=token_org_id,
        customer_account_id=_uuid_to_str(payload.customer_account_id),
        driver_id=effective_driver_id,
        load_id=_uuid_to_str(payload.load_id),
        subject=_normalize_optional_text(payload.subject),
        description=_normalize_optional_text(payload.description),
        status=_normalize_optional_text(payload.status),
        priority=_normalize_optional_text(payload.priority),
        assigned_to_staff_user_id=_uuid_to_str(payload.assigned_to_staff_user_id),
        resolved_at=_normalize_optional_text(payload.resolved_at),
    )

    return ApiResponse(
        data=_serialize_support_ticket(item),
        meta={},
        error=None,
    )
