from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import get_current_token_payload
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




def _resolve_effective_org_id(
    *,
    organization_id: uuid.UUID | None,
    token_payload: dict[str, Any],
) -> uuid.UUID:
    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")
    return effective_org_id


def _assert_item_org(item: Any, *, token_org_id: uuid.UUID) -> None:
    if str(getattr(item, "organization_id", "")) != str(token_org_id):
        raise UnauthorizedError("Resource is not in authenticated organization")


def _get_token_role(token_payload: dict[str, Any]) -> str:
    return str(token_payload.get("role") or "").strip().lower()


def _get_token_driver_id(token_payload: dict[str, Any]) -> str | None:
    token_driver_id = token_payload.get("driver_id")
    if token_driver_id is None:
        return None
    normalized = str(token_driver_id).strip()
    return normalized or None


def _ensure_staff_role_for_mutation(token_payload: dict[str, Any]) -> None:
    if _get_token_role(token_payload) == "driver":
        raise UnauthorizedError("Driver accounts cannot mutate billing invoices")


def _assert_driver_can_access_invoice(
    *,
    item: Any,
    token_payload: dict[str, Any],
) -> None:
    token_role = _get_token_role(token_payload)
    if token_role != "driver":
        return

    token_driver_id = _get_token_driver_id(token_payload)
    if not token_driver_id:
        raise UnauthorizedError("Driver token is missing driver_id")

    payments = getattr(item, "payments", []) or []
    has_driver_payment = any(str(getattr(payment, "driver_id", "")) == token_driver_id for payment in payments)
    if not has_driver_payment:
        raise UnauthorizedError("Drivers may only access invoices tied to their own payments")


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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _ensure_staff_role_for_mutation(token_payload)
    effective_org_id = _resolve_effective_org_id(
        organization_id=payload.organization_id,
        token_payload=token_payload,
    )

    service = InvoiceService(db)
    item = service.create_invoice(
        organization_id=str(effective_org_id),
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_org_id = _resolve_effective_org_id(
        organization_id=organization_id,
        token_payload=token_payload,
    )
    effective_driver_id = driver_id
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if driver_id is not None and str(driver_id) != token_driver_id:
            raise UnauthorizedError("Drivers may only list their own invoices")
        effective_driver_id = uuid.UUID(token_driver_id)

    service = InvoiceService(db)
    items, total = service.list_invoices(
        organization_id=_uuid_to_str(effective_org_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        subscription_id=_uuid_to_str(subscription_id),
        driver_id=_uuid_to_str(effective_driver_id),
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = InvoiceService(db)
    item = service.get_invoice(str(invoice_id))
    token_org_id = uuid.UUID(str(token_payload.get("organization_id")))
    _assert_item_org(item, token_org_id=token_org_id)
    _assert_driver_can_access_invoice(item=item, token_payload=token_payload)

    return ApiResponse(
        data=_serialize_invoice_detail(item),
        meta={},
        error=None,
    )


@router.patch("/billing-invoices/{invoice_id}", response_model=ApiResponse)
def update_billing_invoice(
    invoice_id: uuid.UUID,
    payload: BillingInvoiceUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _ensure_staff_role_for_mutation(token_payload)
    service = InvoiceService(db)
    existing = service.get_invoice(str(invoice_id))
    token_org_id = uuid.UUID(str(token_payload.get("organization_id")))
    _assert_item_org(existing, token_org_id=token_org_id)
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _ensure_staff_role_for_mutation(token_payload)
    service = InvoiceService(db)
    existing = service.get_invoice(str(invoice_id))
    token_org_id = uuid.UUID(str(token_payload.get("organization_id")))
    _assert_item_org(existing, token_org_id=token_org_id)
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
