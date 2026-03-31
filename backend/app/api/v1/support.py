from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.support.support_service import SupportService
from app.services.support.ticket_routing_service import TicketRoutingService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_required_text(value: str) -> str:
    return value.strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
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
        "status": item.status,
        "priority": item.priority,
        "resolved_at": _to_iso_or_none(item.resolved_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/support/tickets", response_model=ApiResponse)
def create_support_ticket(
    *,
    organization_id: uuid.UUID,
    subject: str,
    description: str,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    priority: str = "normal",
    assigned_to_staff_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    normalized_priority = _normalize_required_text(priority)
    normalized_subject = _normalize_required_text(subject)
    normalized_description = _normalize_required_text(description)

    routing = TicketRoutingService().route(
        priority=normalized_priority,
        customer_account_id=_uuid_to_str(customer_account_id),
        load_id=_uuid_to_str(load_id),
    )

    service = SupportService(db)
    item = service.create_ticket(
        organization_id=str(organization_id),
        subject=normalized_subject,
        description=normalized_description,
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        priority=normalized_priority,
        assigned_to_staff_user_id=_uuid_to_str(assigned_to_staff_user_id),
    )

    payload = _serialize_support_ticket(item)
    payload["route"] = routing

    return ApiResponse(
        data=payload,
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
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SupportService(db)
    items, total = service.list_tickets(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
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
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SupportService(db)
    item = service.get_ticket(str(ticket_id))

    return ApiResponse(
        data=_serialize_support_ticket(item),
        meta={},
        error=None,
    )


@router.patch("/support/tickets/{ticket_id}", response_model=ApiResponse)
def update_support_ticket(
    ticket_id: uuid.UUID,
    *,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to_staff_user_id: uuid.UUID | None = None,
    resolved_at: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = SupportService(db)
    item = service.update_ticket(
        ticket_id=str(ticket_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        subject=_normalize_optional_text(subject),
        description=_normalize_optional_text(description),
        status=_normalize_optional_text(status),
        priority=_normalize_optional_text(priority),
        assigned_to_staff_user_id=_uuid_to_str(assigned_to_staff_user_id),
        resolved_at=_normalize_optional_text(resolved_at),
    )

    return ApiResponse(
        data=_serialize_support_ticket(item),
        meta={},
        error=None,
    )