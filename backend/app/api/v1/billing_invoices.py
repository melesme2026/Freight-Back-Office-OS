from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.billing.invoice_service import InvoiceService


router = APIRouter()


@router.post("/billing-invoices", response_model=ApiResponse)
def create_billing_invoice(
    *,
    organization_id: str,
    customer_account_id: str,
    issued_at: str,
    subscription_id: str | None = None,
    due_at: str | None = None,
    billing_period_start: str | None = None,
    billing_period_end: str | None = None,
    currency_code: str = "USD",
    lines: list[dict] | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        uuid.UUID(customer_account_id)
        if subscription_id:
            uuid.UUID(subscription_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "subscription_id": subscription_id,
            },
        ) from exc

    service = InvoiceService(db)
    item = service.create_invoice(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        issued_at=issued_at,
        subscription_id=subscription_id,
        due_at=due_at,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        currency_code=currency_code,
        lines=lines or [],
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "subscription_id": str(item.subscription_id) if item.subscription_id else None,
            "invoice_number": item.invoice_number,
            "status": str(item.status),
            "currency_code": item.currency_code,
            "subtotal_amount": format(item.subtotal_amount, "f"),
            "tax_amount": format(item.tax_amount, "f"),
            "total_amount": format(item.total_amount, "f"),
            "amount_paid": format(item.amount_paid, "f"),
            "amount_due": format(item.amount_due, "f"),
            "issued_at": item.issued_at.isoformat() if hasattr(item.issued_at, "isoformat") else str(item.issued_at),
            "due_at": item.due_at.isoformat() if item.due_at and hasattr(item.due_at, "isoformat") else (str(item.due_at) if item.due_at else None),
            "paid_at": item.paid_at.isoformat() if item.paid_at and hasattr(item.paid_at, "isoformat") else (str(item.paid_at) if item.paid_at else None),
            "billing_period_start": item.billing_period_start.isoformat() if item.billing_period_start and hasattr(item.billing_period_start, "isoformat") else (str(item.billing_period_start) if item.billing_period_start else None),
            "billing_period_end": item.billing_period_end.isoformat() if item.billing_period_end and hasattr(item.billing_period_end, "isoformat") else (str(item.billing_period_end) if item.billing_period_end else None),
            "notes": item.notes,
            "lines": [
                {
                    "id": str(line.id),
                    "invoice_id": str(line.invoice_id),
                    "usage_record_id": str(line.usage_record_id) if line.usage_record_id else None,
                    "line_type": line.line_type,
                    "description": line.description,
                    "quantity": format(line.quantity, "f"),
                    "unit_price": format(line.unit_price, "f"),
                    "line_total": format(line.line_total, "f"),
                    "metadata_json": line.metadata_json,
                    "created_at": line.created_at.isoformat(),
                    "updated_at": line.updated_at.isoformat(),
                }
                for line in item.lines
            ],
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/billing-invoices", response_model=ApiResponse)
def list_billing_invoices(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    subscription_id: str | None = None,
    status: str | None = None,
    due_before: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if subscription_id:
            uuid.UUID(subscription_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "subscription_id": subscription_id,
            },
        ) from exc

    service = InvoiceService(db)
    items, total = service.list_invoices(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        subscription_id=subscription_id,
        status=status,
        due_before=due_before,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "subscription_id": str(item.subscription_id) if item.subscription_id else None,
                "invoice_number": item.invoice_number,
                "status": str(item.status),
                "currency_code": item.currency_code,
                "subtotal_amount": format(item.subtotal_amount, "f"),
                "tax_amount": format(item.tax_amount, "f"),
                "total_amount": format(item.total_amount, "f"),
                "amount_paid": format(item.amount_paid, "f"),
                "amount_due": format(item.amount_due, "f"),
                "issued_at": item.issued_at.isoformat() if hasattr(item.issued_at, "isoformat") else str(item.issued_at),
                "due_at": item.due_at.isoformat() if item.due_at and hasattr(item.due_at, "isoformat") else (str(item.due_at) if item.due_at else None),
                "paid_at": item.paid_at.isoformat() if item.paid_at and hasattr(item.paid_at, "isoformat") else (str(item.paid_at) if item.paid_at else None),
                "billing_period_start": item.billing_period_start.isoformat() if item.billing_period_start and hasattr(item.billing_period_start, "isoformat") else (str(item.billing_period_start) if item.billing_period_start else None),
                "billing_period_end": item.billing_period_end.isoformat() if item.billing_period_end and hasattr(item.billing_period_end, "isoformat") else (str(item.billing_period_end) if item.billing_period_end else None),
                "notes": item.notes,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/billing-invoices/{invoice_id}", response_model=ApiResponse)
def get_billing_invoice(
    invoice_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(invoice_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid invoice_id",
            details={"invoice_id": invoice_id},
        ) from exc

    service = InvoiceService(db)
    item = service.get_invoice(invoice_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "subscription_id": str(item.subscription_id) if item.subscription_id else None,
            "invoice_number": item.invoice_number,
            "status": str(item.status),
            "currency_code": item.currency_code,
            "subtotal_amount": format(item.subtotal_amount, "f"),
            "tax_amount": format(item.tax_amount, "f"),
            "total_amount": format(item.total_amount, "f"),
            "amount_paid": format(item.amount_paid, "f"),
            "amount_due": format(item.amount_due, "f"),
            "issued_at": item.issued_at.isoformat() if hasattr(item.issued_at, "isoformat") else str(item.issued_at),
            "due_at": item.due_at.isoformat() if item.due_at and hasattr(item.due_at, "isoformat") else (str(item.due_at) if item.due_at else None),
            "paid_at": item.paid_at.isoformat() if item.paid_at and hasattr(item.paid_at, "isoformat") else (str(item.paid_at) if item.paid_at else None),
            "billing_period_start": item.billing_period_start.isoformat() if item.billing_period_start and hasattr(item.billing_period_start, "isoformat") else (str(item.billing_period_start) if item.billing_period_start else None),
            "billing_period_end": item.billing_period_end.isoformat() if item.billing_period_end and hasattr(item.billing_period_end, "isoformat") else (str(item.billing_period_end) if item.billing_period_end else None),
            "notes": item.notes,
            "lines": [
                {
                    "id": str(line.id),
                    "invoice_id": str(line.invoice_id),
                    "usage_record_id": str(line.usage_record_id) if line.usage_record_id else None,
                    "line_type": line.line_type,
                    "description": line.description,
                    "quantity": format(line.quantity, "f"),
                    "unit_price": format(line.unit_price, "f"),
                    "line_total": format(line.line_total, "f"),
                    "metadata_json": line.metadata_json,
                    "created_at": line.created_at.isoformat(),
                    "updated_at": line.updated_at.isoformat(),
                }
                for line in item.lines
            ],
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/billing-invoices/{invoice_id}", response_model=ApiResponse)
def update_billing_invoice(
    invoice_id: str,
    *,
    status: str | None = None,
    issued_at: str | None = None,
    due_at: str | None = None,
    paid_at: str | None = None,
    billing_period_start: str | None = None,
    billing_period_end: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(invoice_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid invoice_id",
            details={"invoice_id": invoice_id},
        ) from exc

    service = InvoiceService(db)
    item = service.update_invoice(
        invoice_id=invoice_id,
        status=status,
        issued_at=issued_at,
        due_at=due_at,
        paid_at=paid_at,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "subtotal_amount": format(item.subtotal_amount, "f"),
            "tax_amount": format(item.tax_amount, "f"),
            "total_amount": format(item.total_amount, "f"),
            "amount_paid": format(item.amount_paid, "f"),
            "amount_due": format(item.amount_due, "f"),
            "issued_at": item.issued_at.isoformat() if hasattr(item.issued_at, "isoformat") else str(item.issued_at),
            "due_at": item.due_at.isoformat() if item.due_at and hasattr(item.due_at, "isoformat") else (str(item.due_at) if item.due_at else None),
            "paid_at": item.paid_at.isoformat() if item.paid_at and hasattr(item.paid_at, "isoformat") else (str(item.paid_at) if item.paid_at else None),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/billing-invoices/{invoice_id}/mark-past-due", response_model=ApiResponse)
def mark_billing_invoice_past_due(
    invoice_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(invoice_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid invoice_id",
            details={"invoice_id": invoice_id},
        ) from exc

    service = InvoiceService(db)
    item = service.mark_past_due(invoice_id=invoice_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "amount_due": format(item.amount_due, "f"),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )