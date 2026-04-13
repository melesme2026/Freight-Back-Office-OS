from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.billing.invoice_service import InvoiceService


router = APIRouter()


class BillingInvoiceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    customer_account_id: uuid.UUID
    issued_at: str
    subscription_id: uuid.UUID | None = None
    due_at: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    currency_code: str = "USD"
    lines: list[dict[str, Any]] | None = None
    notes: str | None = None


class BillingInvoiceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    issued_at: str | None = None
    due_at: str | None = None
    paid_at: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    notes: str | None = None


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _decimal_to_string(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")

    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, TypeError, ValueError):
        return str(value)


def _datetime_to_iso(value: object | None) -> str | None:
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


def _serialize_invoice_line(line: Any) -> dict[str, Any]:
    return {
        "id": str(line.id),
        "invoice_id": str(line.invoice_id),
        "usage_record_id": str(line.usage_record_id) if line.usage_record_id else None,
        "line_type": line.line_type,
        "description": line.description,
        "quantity": _decimal_to_string(line.quantity),
        "unit_price": _decimal_to_string(line.unit_price),
        "line_total": _decimal_to_string(line.line_total),
        "metadata_json": line.metadata_json,
        "created_at": _datetime_to_iso(line.created_at),
        "updated_at": _datetime_to_iso(line.updated_at),
    }


def _serialize_invoice_base(invoice: Any) -> dict[str, Any]:
    return {
        "id": str(invoice.id),
        "organization_id": str(invoice.organization_id),
        "customer_account_id": str(invoice.customer_account_id),
        "subscription_id": (
            str(invoice.subscription_id) if invoice.subscription_id else None
        ),
        "invoice_number": invoice.invoice_number,
        "status": _enum_to_string(invoice.status),
        "currency_code": invoice.currency_code,
        "subtotal_amount": _decimal_to_string(invoice.subtotal_amount),
        "tax_amount": _decimal_to_string(invoice.tax_amount),
        "total_amount": _decimal_to_string(invoice.total_amount),
        "amount_paid": _decimal_to_string(invoice.amount_paid),
        "amount_due": _decimal_to_string(invoice.amount_due),
        "issued_at": _datetime_to_iso(invoice.issued_at),
        "due_at": _datetime_to_iso(invoice.due_at),
        "paid_at": _datetime_to_iso(invoice.paid_at),
        "billing_period_start": _datetime_to_iso(invoice.billing_period_start),
        "billing_period_end": _datetime_to_iso(invoice.billing_period_end),
        "notes": invoice.notes,
        "created_at": _datetime_to_iso(invoice.created_at),
        "updated_at": _datetime_to_iso(invoice.updated_at),
    }


def _serialize_invoice_summary(invoice: Any) -> dict[str, Any]:
    return _serialize_invoice_base(invoice)


def _serialize_invoice_detail(invoice: Any) -> dict[str, Any]:
    payload = _serialize_invoice_base(invoice)
    payload["lines"] = [_serialize_invoice_line(line) for line in invoice.lines]
    return payload


def _serialize_invoice_update(invoice: Any) -> dict[str, Any]:
    return {
        "id": str(invoice.id),
        "status": _enum_to_string(invoice.status),
        "subtotal_amount": _decimal_to_string(invoice.subtotal_amount),
        "tax_amount": _decimal_to_string(invoice.tax_amount),
        "total_amount": _decimal_to_string(invoice.total_amount),
        "amount_paid": _decimal_to_string(invoice.amount_paid),
        "amount_due": _decimal_to_string(invoice.amount_due),
        "issued_at": _datetime_to_iso(invoice.issued_at),
        "due_at": _datetime_to_iso(invoice.due_at),
        "paid_at": _datetime_to_iso(invoice.paid_at),
        "updated_at": _datetime_to_iso(invoice.updated_at),
    }


@router.post("/billing-invoices", response_model=ApiResponse)
def create_billing_invoice(
    payload: BillingInvoiceCreateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    item = service.create_invoice(
        organization_id=str(payload.organization_id),
        customer_account_id=str(payload.customer_account_id),
        issued_at=payload.issued_at,
        subscription_id=_uuid_to_str(payload.subscription_id),
        due_at=payload.due_at,
        billing_period_start=payload.billing_period_start,
        billing_period_end=payload.billing_period_end,
        currency_code=payload.currency_code.strip().upper(),
        lines=payload.lines or [],
        notes=_normalize_optional_text(payload.notes),
    )

    return ApiResponse(
        data=_serialize_invoice_detail(item),
        meta={},
        error=None,
    )


@router.get("/billing-invoices", response_model=ApiResponse)
def list_billing_invoices(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    subscription_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    status: str | None = None,
    due_before: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    items, total = service.list_invoices(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        subscription_id=_uuid_to_str(subscription_id),
        driver_id=_uuid_to_str(driver_id),
        status=_normalize_optional_text(status),
        due_before=_normalize_optional_text(due_before),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_invoice_summary(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/billing-invoices/{invoice_id}", response_model=ApiResponse)
def get_billing_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    item = service.get_invoice(str(invoice_id))

    return ApiResponse(
        data=_serialize_invoice_detail(item),
        meta={},
        error=None,
    )


@router.patch("/billing-invoices/{invoice_id}", response_model=ApiResponse)
def update_billing_invoice(
    invoice_id: uuid.UUID,
    payload: BillingInvoiceUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    item = service.update_invoice(
        invoice_id=str(invoice_id),
        status=_normalize_optional_text(payload.status),
        issued_at=_normalize_optional_text(payload.issued_at),
        due_at=_normalize_optional_text(payload.due_at),
        paid_at=_normalize_optional_text(payload.paid_at),
        billing_period_start=_normalize_optional_text(payload.billing_period_start),
        billing_period_end=_normalize_optional_text(payload.billing_period_end),
        notes=_normalize_optional_text(payload.notes),
    )

    return ApiResponse(
        data=_serialize_invoice_update(item),
        meta={},
        error=None,
    )


@router.post("/billing-invoices/{invoice_id}/mark-past-due", response_model=ApiResponse)
def mark_billing_invoice_past_due(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    item = service.mark_past_due(invoice_id=str(invoice_id))

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": _enum_to_string(item.status),
            "amount_due": _decimal_to_string(item.amount_due),
            "updated_at": _datetime_to_iso(item.updated_at),
        },
        meta={},
        error=None,
    )
