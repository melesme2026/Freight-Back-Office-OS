from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.domain.enums.load_status import LoadStatus
from app.schemas.common import ApiResponse
from app.services.loads.load_service import LoadService
from app.services.workflow.workflow_engine import WorkflowEngine


router = APIRouter()


@router.post("/loads", response_model=ApiResponse)
def create_load(
    *,
    organization_id: str,
    customer_account_id: str,
    driver_id: str,
    broker_id: str | None = None,
    source_channel: str = "manual",
    load_number: str | None = None,
    rate_confirmation_number: str | None = None,
    bol_number: str | None = None,
    invoice_number: str | None = None,
    broker_name_raw: str | None = None,
    broker_email_raw: str | None = None,
    pickup_date: str | None = None,
    delivery_date: str | None = None,
    pickup_location: str | None = None,
    delivery_location: str | None = None,
    gross_amount: str | None = None,
    currency_code: str = "USD",
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        uuid.UUID(customer_account_id)
        uuid.UUID(driver_id)
        if broker_id:
            uuid.UUID(broker_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "broker_id": broker_id,
            },
        ) from exc

    amount_value = Decimal(gross_amount) if gross_amount is not None else None

    service = LoadService(db)
    item = service.create_load(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        broker_id=broker_id,
        source_channel=source_channel,
        load_number=load_number,
        rate_confirmation_number=rate_confirmation_number,
        bol_number=bol_number,
        invoice_number=invoice_number,
        broker_name_raw=broker_name_raw,
        broker_email_raw=broker_email_raw,
        pickup_date=pickup_date,
        delivery_date=delivery_date,
        pickup_location=pickup_location,
        delivery_location=delivery_location,
        gross_amount=amount_value,
        currency_code=currency_code,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "driver_id": str(item.driver_id),
            "broker_id": str(item.broker_id) if item.broker_id else None,
            "source_channel": str(item.source_channel),
            "status": str(item.status),
            "processing_status": str(item.processing_status),
            "load_number": item.load_number,
            "rate_confirmation_number": item.rate_confirmation_number,
            "bol_number": item.bol_number,
            "invoice_number": item.invoice_number,
            "broker_name_raw": item.broker_name_raw,
            "broker_email_raw": item.broker_email_raw,
            "pickup_date": item.pickup_date.isoformat() if item.pickup_date else None,
            "delivery_date": item.delivery_date.isoformat() if item.delivery_date else None,
            "pickup_location": item.pickup_location,
            "delivery_location": item.delivery_location,
            "gross_amount": format(item.gross_amount, "f") if item.gross_amount is not None else None,
            "currency_code": item.currency_code,
            "documents_complete": item.documents_complete,
            "has_ratecon": item.has_ratecon,
            "has_bol": item.has_bol,
            "has_invoice": item.has_invoice,
            "extraction_confidence_avg": format(item.extraction_confidence_avg, "f") if item.extraction_confidence_avg is not None else None,
            "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
            "funded_at": item.funded_at.isoformat() if item.funded_at else None,
            "paid_at": item.paid_at.isoformat() if item.paid_at else None,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/loads", response_model=ApiResponse)
def list_loads(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    status: str | None = None,
    source_channel: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
            },
        ) from exc

    service = LoadService(db)
    items, total = service.list_loads(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        status=status,
        source_channel=source_channel,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "driver_id": str(item.driver_id),
                "broker_id": str(item.broker_id) if item.broker_id else None,
                "source_channel": str(item.source_channel),
                "status": str(item.status),
                "processing_status": str(item.processing_status),
                "load_number": item.load_number,
                "rate_confirmation_number": item.rate_confirmation_number,
                "bol_number": item.bol_number,
                "invoice_number": item.invoice_number,
                "gross_amount": format(item.gross_amount, "f") if item.gross_amount is not None else None,
                "currency_code": item.currency_code,
                "pickup_date": item.pickup_date.isoformat() if item.pickup_date else None,
                "delivery_date": item.delivery_date.isoformat() if item.delivery_date else None,
                "documents_complete": item.documents_complete,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/loads/{load_id}", response_model=ApiResponse)
def get_load(
    load_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(load_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid load_id",
            details={"load_id": load_id},
        ) from exc

    service = LoadService(db)
    item = service.get_load(load_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "driver_id": str(item.driver_id),
            "broker_id": str(item.broker_id) if item.broker_id else None,
            "source_channel": str(item.source_channel),
            "status": str(item.status),
            "processing_status": str(item.processing_status),
            "load_number": item.load_number,
            "rate_confirmation_number": item.rate_confirmation_number,
            "bol_number": item.bol_number,
            "invoice_number": item.invoice_number,
            "broker_name_raw": item.broker_name_raw,
            "broker_email_raw": item.broker_email_raw,
            "pickup_date": item.pickup_date.isoformat() if item.pickup_date else None,
            "delivery_date": item.delivery_date.isoformat() if item.delivery_date else None,
            "pickup_location": item.pickup_location,
            "delivery_location": item.delivery_location,
            "gross_amount": format(item.gross_amount, "f") if item.gross_amount is not None else None,
            "currency_code": item.currency_code,
            "documents_complete": item.documents_complete,
            "has_ratecon": item.has_ratecon,
            "has_bol": item.has_bol,
            "has_invoice": item.has_invoice,
            "extraction_confidence_avg": format(item.extraction_confidence_avg, "f") if item.extraction_confidence_avg is not None else None,
            "last_reviewed_by": str(item.last_reviewed_by) if item.last_reviewed_by else None,
            "last_reviewed_at": item.last_reviewed_at.isoformat() if item.last_reviewed_at else None,
            "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
            "funded_at": item.funded_at.isoformat() if item.funded_at else None,
            "paid_at": item.paid_at.isoformat() if item.paid_at else None,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/loads/{load_id}", response_model=ApiResponse)
def update_load(
    load_id: str,
    *,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    broker_id: str | None = None,
    source_channel: str | None = None,
    load_number: str | None = None,
    rate_confirmation_number: str | None = None,
    bol_number: str | None = None,
    invoice_number: str | None = None,
    broker_name_raw: str | None = None,
    broker_email_raw: str | None = None,
    pickup_date: str | None = None,
    delivery_date: str | None = None,
    pickup_location: str | None = None,
    delivery_location: str | None = None,
    gross_amount: str | None = None,
    currency_code: str | None = None,
    documents_complete: bool | None = None,
    has_ratecon: bool | None = None,
    has_bol: bool | None = None,
    has_invoice: bool | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(load_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if broker_id:
            uuid.UUID(broker_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "load_id": load_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "broker_id": broker_id,
            },
        ) from exc

    service = LoadService(db)
    item = service.update_load(
        load_id=load_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        broker_id=broker_id,
        source_channel=source_channel,
        load_number=load_number,
        rate_confirmation_number=rate_confirmation_number,
        bol_number=bol_number,
        invoice_number=invoice_number,
        broker_name_raw=broker_name_raw,
        broker_email_raw=broker_email_raw,
        pickup_date=pickup_date,
        delivery_date=delivery_date,
        pickup_location=pickup_location,
        delivery_location=delivery_location,
        gross_amount=Decimal(gross_amount) if gross_amount is not None else None,
        currency_code=currency_code,
        documents_complete=documents_complete,
        has_ratecon=has_ratecon,
        has_bol=has_bol,
        has_invoice=has_invoice,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "driver_id": str(item.driver_id),
            "broker_id": str(item.broker_id) if item.broker_id else None,
            "source_channel": str(item.source_channel),
            "status": str(item.status),
            "processing_status": str(item.processing_status),
            "load_number": item.load_number,
            "rate_confirmation_number": item.rate_confirmation_number,
            "bol_number": item.bol_number,
            "invoice_number": item.invoice_number,
            "broker_name_raw": item.broker_name_raw,
            "broker_email_raw": item.broker_email_raw,
            "pickup_date": item.pickup_date.isoformat() if item.pickup_date else None,
            "delivery_date": item.delivery_date.isoformat() if item.delivery_date else None,
            "pickup_location": item.pickup_location,
            "delivery_location": item.delivery_location,
            "gross_amount": format(item.gross_amount, "f") if item.gross_amount is not None else None,
            "currency_code": item.currency_code,
            "documents_complete": item.documents_complete,
            "has_ratecon": item.has_ratecon,
            "has_bol": item.has_bol,
            "has_invoice": item.has_invoice,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/loads/{load_id}/status", response_model=ApiResponse)
def transition_load_status(
    load_id: str,
    *,
    new_status: str,
    actor_staff_user_id: str | None = None,
    actor_type: str = "system",
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(load_id)
        if actor_staff_user_id:
            uuid.UUID(actor_staff_user_id)
        parsed_status = LoadStatus(new_status)
    except ValueError as exc:
        raise ValidationError(
            "Invalid status transition input",
            details={
                "load_id": load_id,
                "new_status": new_status,
                "actor_staff_user_id": actor_staff_user_id,
            },
        ) from exc

    engine = WorkflowEngine(db)
    result = engine.transition_load(
        load_id=load_id,
        new_status=parsed_status,
        actor_staff_user_id=actor_staff_user_id,
        actor_type=actor_type,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": result["id"],
            "old_status": str(result["old_status"]) if result["old_status"] else None,
            "new_status": str(result["new_status"]),
            "changed_at": result["changed_at"].isoformat(),
        },
        meta={},
        error=None,
    )