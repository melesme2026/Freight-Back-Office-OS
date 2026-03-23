from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.support.support_service import SupportService
from app.services.support.ticket_routing_service import TicketRoutingService


router = APIRouter()


@router.post("/support/tickets", response_model=ApiResponse)
def create_support_ticket(
    *,
    organization_id: str,
    subject: str,
    description: str,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    priority: str = "normal",
    assigned_to_staff_user_id: str | None = None,
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
        if assigned_to_staff_user_id:
            uuid.UUID(assigned_to_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
                "assigned_to_staff_user_id": assigned_to_staff_user_id,
            },
        ) from exc

    routing = TicketRoutingService().route(
        priority=priority,
        customer_account_id=customer_account_id,
        load_id=load_id,
    )

    service = SupportService(db)
    item = service.create_ticket(
        organization_id=organization_id,
        subject=subject,
        description=description,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        priority=priority,
        assigned_to_staff_user_id=assigned_to_staff_user_id,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "assigned_to_staff_user_id": str(item.assigned_to_staff_user_id) if item.assigned_to_staff_user_id else None,
            "subject": item.subject,
            "description": item.description,
            "status": item.status,
            "priority": item.priority,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "route": routing,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/support/tickets", response_model=ApiResponse)
def list_support_tickets(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    assigned_to_staff_user_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
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
        if assigned_to_staff_user_id:
            uuid.UUID(assigned_to_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
                "assigned_to_staff_user_id": assigned_to_staff_user_id,
            },
        ) from exc

    service = SupportService(db)
    items, total = service.list_tickets(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        assigned_to_staff_user_id=assigned_to_staff_user_id,
        status=status,
        priority=priority,
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
                "driver_id": str(item.driver_id) if item.driver_id else None,
                "load_id": str(item.load_id) if item.load_id else None,
                "assigned_to_staff_user_id": str(item.assigned_to_staff_user_id) if item.assigned_to_staff_user_id else None,
                "subject": item.subject,
                "description": item.description,
                "status": item.status,
                "priority": item.priority,
                "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/support/tickets/{ticket_id}", response_model=ApiResponse)
def get_support_ticket(
    ticket_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(ticket_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid ticket_id",
            details={"ticket_id": ticket_id},
        ) from exc

    service = SupportService(db)
    item = service.get_ticket(ticket_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "assigned_to_staff_user_id": str(item.assigned_to_staff_user_id) if item.assigned_to_staff_user_id else None,
            "subject": item.subject,
            "description": item.description,
            "status": item.status,
            "priority": item.priority,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/support/tickets/{ticket_id}", response_model=ApiResponse)
def update_support_ticket(
    ticket_id: str,
    *,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to_staff_user_id: str | None = None,
    resolved_at: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(ticket_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if load_id:
            uuid.UUID(load_id)
        if assigned_to_staff_user_id:
            uuid.UUID(assigned_to_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "ticket_id": ticket_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
                "assigned_to_staff_user_id": assigned_to_staff_user_id,
            },
        ) from exc

    service = SupportService(db)
    item = service.update_ticket(
        ticket_id=ticket_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        subject=subject,
        description=description,
        status=status,
        priority=priority,
        assigned_to_staff_user_id=assigned_to_staff_user_id,
        resolved_at=resolved_at,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "assigned_to_staff_user_id": str(item.assigned_to_staff_user_id) if item.assigned_to_staff_user_id else None,
            "subject": item.subject,
            "description": item.description,
            "status": item.status,
            "priority": item.priority,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )