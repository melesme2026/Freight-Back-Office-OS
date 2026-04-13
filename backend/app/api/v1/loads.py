from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.security import get_current_token_payload
from app.core.exceptions import UnauthorizedError, ValidationError
from app.domain.enums.load_status import LoadStatus
from app.schemas.common import ApiResponse
from app.services.loads.load_service import LoadService
from app.services.workflow.workflow_engine import WorkflowEngine


router = APIRouter()


class LoadCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    customer_account_id: uuid.UUID
    driver_id: uuid.UUID
    broker_id: uuid.UUID | None = None
    source_channel: str = "manual"
    load_number: str | None = None
    rate_confirmation_number: str | None = None
    bol_number: str | None = None
    invoice_number: str | None = None
    broker_name_raw: str | None = None
    broker_email_raw: str | None = None
    pickup_date: str | None = None
    delivery_date: str | None = None
    pickup_location: str | None = None
    delivery_location: str | None = None
    gross_amount: str | None = None
    currency_code: str = "USD"
    notes: str | None = None


class LoadUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    broker_id: uuid.UUID | None = None
    source_channel: str | None = None
    load_number: str | None = None
    rate_confirmation_number: str | None = None
    bol_number: str | None = None
    invoice_number: str | None = None
    broker_name_raw: str | None = None
    broker_email_raw: str | None = None
    pickup_date: str | None = None
    delivery_date: str | None = None
    pickup_location: str | None = None
    delivery_location: str | None = None
    gross_amount: str | None = None
    currency_code: str | None = None
    documents_complete: bool | None = None
    has_ratecon: bool | None = None
    has_bol: bool | None = None
    has_invoice: bool | None = None
    notes: str | None = None


class LoadStatusTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: str
    actor_staff_user_id: uuid.UUID | None = None
    actor_type: str = "system"
    notes: str | None = None


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


def _parse_load_status(value: str) -> LoadStatus:
    normalized = _normalize_required_text(value, "new_status").strip().lower()

    for status in LoadStatus:
        if normalized == status.value.lower():
            return status
        if normalized == status.name.lower():
            return status

    raise ValidationError(
        "Invalid new_status",
        details={"new_status": value},
    )


def _serialize_load(item: Any, *, detailed: bool = False) -> dict[str, Any]:
    customer_account = getattr(item, "customer_account", None)
    driver = getattr(item, "driver", None)
    broker = getattr(item, "broker", None)
    workflow_events = getattr(item, "workflow_events", None)
    validation_issues = getattr(item, "validation_issues", None)
    documents = getattr(item, "documents", None)
    last_reviewed_by_user = getattr(item, "last_reviewed_by_user", None)

    payload = {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "customer_account_name": (
            getattr(customer_account, "account_name", None) if customer_account else None
        ),
        "driver_id": str(item.driver_id),
        "driver_name": getattr(driver, "full_name", None) if driver else None,
        "broker_id": str(item.broker_id) if item.broker_id else None,
        "broker_name": getattr(broker, "name", None) if broker else None,
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
                "last_reviewed_by_name": (
                    getattr(last_reviewed_by_user, "full_name", None)
                    if last_reviewed_by_user
                    else None
                ),
                "last_reviewed_at": _to_iso_or_none(
                    getattr(item, "last_reviewed_at", None)
                ),
                "submitted_at": _to_iso_or_none(item.submitted_at),
                "funded_at": _to_iso_or_none(item.funded_at),
                "paid_at": _to_iso_or_none(item.paid_at),
                "notes": item.notes,
                "document_count": len(documents) if isinstance(documents, list) else None,
                "validation_issue_count": (
                    len(validation_issues) if isinstance(validation_issues, list) else None
                ),
                "workflow_event_count": (
                    len(workflow_events) if isinstance(workflow_events, list) else None
                ),
            }
        )

    return payload


@router.post("/loads", response_model=ApiResponse)
def create_load(
    payload: LoadCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    service = LoadService(db)
    item = service.create_load(
        organization_id=str(payload.organization_id),
        customer_account_id=str(payload.customer_account_id),
        driver_id=str(payload.driver_id),
        broker_id=_uuid_to_str(payload.broker_id),
        source_channel=_normalize_required_text(payload.source_channel, "source_channel"),
        load_number=_normalize_optional_text(payload.load_number),
        rate_confirmation_number=_normalize_optional_text(payload.rate_confirmation_number),
        bol_number=_normalize_optional_text(payload.bol_number),
        invoice_number=_normalize_optional_text(payload.invoice_number),
        broker_name_raw=_normalize_optional_text(payload.broker_name_raw),
        broker_email_raw=_normalize_email(payload.broker_email_raw),
        pickup_date=_normalize_optional_text(payload.pickup_date),
        delivery_date=_normalize_optional_text(payload.delivery_date),
        pickup_location=_normalize_optional_text(payload.pickup_location),
        delivery_location=_normalize_optional_text(payload.delivery_location),
        gross_amount=_parse_decimal(payload.gross_amount, "gross_amount"),
        currency_code=_normalize_currency_code(payload.currency_code) or "USD",
        notes=_normalize_optional_text(payload.notes),
    )

    item = service.get_load(str(item.id))

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.get("/loads", response_model=ApiResponse)
def list_loads(
    *,
    organization_id: uuid.UUID | None = None,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
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
    token_org_id = token_payload.get("organization_id")
    token_role = str(token_payload.get("role") or "").lower()
    token_driver_id = token_payload.get("driver_id")

    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    effective_driver_id = driver_id
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if driver_id is not None and str(driver_id) != str(token_driver_id):
            raise UnauthorizedError("Driver may only access own loads")
        effective_driver_id = uuid.UUID(str(token_driver_id))

    service = LoadService(db)
    items, total = service.list_loads(
        organization_id=_uuid_to_str(effective_org_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(effective_driver_id),
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
    payload: LoadUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    item = service.update_load(
        load_id=str(load_id),
        customer_account_id=_uuid_to_str(payload.customer_account_id),
        driver_id=_uuid_to_str(payload.driver_id),
        broker_id=_uuid_to_str(payload.broker_id),
        source_channel=_normalize_optional_text(payload.source_channel),
        load_number=_normalize_optional_text(payload.load_number),
        rate_confirmation_number=_normalize_optional_text(payload.rate_confirmation_number),
        bol_number=_normalize_optional_text(payload.bol_number),
        invoice_number=_normalize_optional_text(payload.invoice_number),
        broker_name_raw=_normalize_optional_text(payload.broker_name_raw),
        broker_email_raw=_normalize_email(payload.broker_email_raw),
        pickup_date=_normalize_optional_text(payload.pickup_date),
        delivery_date=_normalize_optional_text(payload.delivery_date),
        pickup_location=_normalize_optional_text(payload.pickup_location),
        delivery_location=_normalize_optional_text(payload.delivery_location),
        gross_amount=_parse_decimal(payload.gross_amount, "gross_amount"),
        currency_code=_normalize_currency_code(payload.currency_code),
        documents_complete=payload.documents_complete,
        has_ratecon=payload.has_ratecon,
        has_bol=payload.has_bol,
        has_invoice=payload.has_invoice,
        notes=_normalize_optional_text(payload.notes),
    )

    item = service.get_load(str(item.id))

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.post("/loads/{load_id}/status", response_model=ApiResponse)
def transition_load_status(
    load_id: uuid.UUID,
    payload: LoadStatusTransitionRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    parsed_status = _parse_load_status(payload.new_status)

    engine = WorkflowEngine(db)
    result = engine.transition_load(
        load_id=str(load_id),
        new_status=parsed_status,
        actor_staff_user_id=_uuid_to_str(payload.actor_staff_user_id),
        actor_type=_normalize_required_text(payload.actor_type, "actor_type"),
        notes=_normalize_optional_text(payload.notes),
    )

    return ApiResponse(
        data={
            "id": result["id"],
            "old_status": result["old_status"],
            "new_status": result["new_status"],
            "changed_at": result["changed_at"],
        },
        meta={},
        error=None,
    )

@router.get("/loads/export.csv")
def export_loads_csv(
    *,
    organization_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    status: str | None = None,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
):
    token_org_id = token_payload.get("organization_id")
    if not token_org_id:
        raise ValidationError("Token organization_id is missing", details={"organization_id": None})

    effective_org_id = str(organization_id) if organization_id else str(token_org_id)
    if str(token_org_id) != effective_org_id:
        raise ValidationError(
            "organization_id does not match authenticated organization",
            details={"organization_id": effective_org_id},
        )

    service = LoadService(db)
    items, _ = service.list_loads(
        organization_id=effective_org_id,
        driver_id=_uuid_to_str(driver_id),
        status=_normalize_optional_text(status),
        page=1,
        page_size=500,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "load_id",
        "load_number",
        "status",
        "driver_id",
        "customer_account_id",
        "broker_id",
        "gross_amount",
        "currency_code",
        "pickup_date",
        "delivery_date",
        "created_at",
        "updated_at",
    ])

    for item in items:
        row = _serialize_load(item, detailed=False)
        writer.writerow([
            row.get("id"),
            row.get("load_number"),
            row.get("status"),
            row.get("driver_id"),
            row.get("customer_account_id"),
            row.get("broker_id"),
            row.get("gross_amount"),
            row.get("currency_code"),
            row.get("pickup_date"),
            row.get("delivery_date"),
            row.get("created_at"),
            row.get("updated_at"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="loads-export.csv"'},
    )
