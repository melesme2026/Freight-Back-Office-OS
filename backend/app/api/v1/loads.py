from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.domain.enums.load_status import LoadStatus
from app.schemas.common import ApiResponse
from app.services.loads.load_service import LoadService
from app.services.workflow.workflow_engine import WorkflowEngine


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str, field_name: str = "value") -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _normalize_currency_code(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.upper() if normalized else None


def _parse_decimal(value: str | None, field_name: str) -> Decimal | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValidationError(
            f"Invalid {field_name}",
            details={field_name: value},
        ) from exc


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _to_decimal_string(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _serialize_load(item: Any, *, detailed: bool = False) -> dict[str, Any]:
    payload = {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "driver_id": str(item.driver_id),
        "broker_id": str(item.broker_id) if item.broker_id else None,
        "source_channel": _enum_to_string(item.source_channel),
        "status": _enum_to_string(item.status),
        "processing_status": _enum_to_string(item.processing_status),
        "load_number": item.load_number,
        "rate_confirmation_number": item.rate_confirmation_number,
        "bol_number": item.bol_number,
        "invoice_number": item.invoice_number,
        "gross_amount": _to_decimal_string(item.gross_amount),
        "currency_code": item.currency_code,
        "pickup_date": _to_iso_or_none(item.pickup_date),
        "delivery_date": _to_iso_or_none(item.delivery_date),
        "documents_complete": item.documents_complete,
        "has_ratecon": item.has_ratecon,
        "has_bol": item.has_bol,
        "has_invoice": item.has_invoice,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }

    if detailed:
        payload.update(
            {
                "broker_name_raw": item.broker_name_raw,
                "broker_email_raw": item.broker_email_raw,
                "pickup_location": item.pickup_location,
                "delivery_location": item.delivery_location,
                "extraction_confidence_avg": _to_decimal_string(
                    item.extraction_confidence_avg
                ),
                "last_reviewed_by": (
                    str(item.last_reviewed_by)
                    if getattr(item, "last_reviewed_by", None)
                    else None
                ),
                "last_reviewed_at": _to_iso_or_none(
                    getattr(item, "last_reviewed_at", None)
                ),
                "submitted_at": _to_iso_or_none(item.submitted_at),
                "funded_at": _to_iso_or_none(item.funded_at),
                "paid_at": _to_iso_or_none(item.paid_at),
                "notes": item.notes,
            }
        )

    return payload


@router.post("/loads", response_model=ApiResponse)
def create_load(
    *,
    organization_id: uuid.UUID,
    customer_account_id: uuid.UUID,
    driver_id: uuid.UUID,
    broker_id: uuid.UUID | None = None,
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
    service = LoadService(db)
    item = service.create_load(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        driver_id=str(driver_id),
        broker_id=_uuid_to_str(broker_id),
        source_channel=_normalize_required_text(source_channel, "source_channel"),
        load_number=_normalize_optional_text(load_number),
        rate_confirmation_number=_normalize_optional_text(rate_confirmation_number),
        bol_number=_normalize_optional_text(bol_number),
        invoice_number=_normalize_optional_text(invoice_number),
        broker_name_raw=_normalize_optional_text(broker_name_raw),
        broker_email_raw=_normalize_email(broker_email_raw),
        pickup_date=_normalize_optional_text(pickup_date),
        delivery_date=_normalize_optional_text(delivery_date),
        pickup_location=_normalize_optional_text(pickup_location),
        delivery_location=_normalize_optional_text(delivery_location),
        gross_amount=_parse_decimal(gross_amount, "gross_amount"),
        currency_code=_normalize_currency_code(currency_code) or "USD",
        notes=_normalize_optional_text(notes),
    )

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.get("/loads", response_model=ApiResponse)
def list_loads(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    status: str | None = None,
    source_channel: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    items, total = service.list_loads(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        status=_normalize_optional_text(status),
        source_channel=_normalize_optional_text(source_channel),
        date_from=_normalize_optional_text(date_from),
        date_to=_normalize_optional_text(date_to),
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_load(item, detailed=False) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/loads/{load_id}", response_model=ApiResponse)
def get_load(
    load_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    item = service.get_load(str(load_id))

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.patch("/loads/{load_id}", response_model=ApiResponse)
def update_load(
    load_id: uuid.UUID,
    *,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    broker_id: uuid.UUID | None = None,
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
    service = LoadService(db)
    item = service.update_load(
        load_id=str(load_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        broker_id=_uuid_to_str(broker_id),
        source_channel=_normalize_optional_text(source_channel),
        load_number=_normalize_optional_text(load_number),
        rate_confirmation_number=_normalize_optional_text(rate_confirmation_number),
        bol_number=_normalize_optional_text(bol_number),
        invoice_number=_normalize_optional_text(invoice_number),
        broker_name_raw=_normalize_optional_text(broker_name_raw),
        broker_email_raw=_normalize_email(broker_email_raw),
        pickup_date=_normalize_optional_text(pickup_date),
        delivery_date=_normalize_optional_text(delivery_date),
        pickup_location=_normalize_optional_text(pickup_location),
        delivery_location=_normalize_optional_text(delivery_location),
        gross_amount=_parse_decimal(gross_amount, "gross_amount"),
        currency_code=_normalize_currency_code(currency_code),
        documents_complete=documents_complete,
        has_ratecon=has_ratecon,
        has_bol=has_bol,
        has_invoice=has_invoice,
        notes=_normalize_optional_text(notes),
    )

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.post("/loads/{load_id}/status", response_model=ApiResponse)
def transition_load_status(
    load_id: uuid.UUID,
    *,
    new_status: str,
    actor_staff_user_id: uuid.UUID | None = None,
    actor_type: str = "system",
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    normalized_status = _normalize_required_text(new_status, "new_status")

    try:
        parsed_status = LoadStatus(normalized_status)
    except ValueError as exc:
        raise ValidationError(
            "Invalid new_status",
            details={"new_status": new_status},
        ) from exc

    engine = WorkflowEngine(db)
    result = engine.transition_load(
        load_id=str(load_id),
        new_status=parsed_status,
        actor_staff_user_id=_uuid_to_str(actor_staff_user_id),
        actor_type=_normalize_required_text(actor_type, "actor_type"),
        notes=_normalize_optional_text(notes),
    )

    return ApiResponse(
        data={
            "id": result["id"],
            "old_status": (
                _enum_to_string(result["old_status"])
                if result["old_status"] is not None
                else None
            ),
            "new_status": _enum_to_string(result["new_status"]),
            "changed_at": result["changed_at"].isoformat(),
        },
        meta={},
        error=None,
    )