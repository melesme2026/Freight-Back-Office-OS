from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.security import get_current_token_payload
from app.core.exceptions import UnauthorizedError, ValidationError
from app.domain.enums.document_type import DocumentType
from app.domain.enums.load_status import LoadStatus
from app.schemas.common import ApiResponse
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.load_service import LoadService
from app.services.loads.operational_queue_service import OperationalQueueService
from app.services.loads.packet_readiness import calculate_packet_readiness
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
    follow_up_required: bool | None = None
    notes: str | None = None


class LoadStatusTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: str
    actor_staff_user_id: uuid.UUID | None = None
    actor_type: str = "system"
    notes: str | None = None


class LoadWorkflowActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    actor_staff_user_id: uuid.UUID | None = None
    actor_type: str = "system"
    follow_up_required: bool | None = None
    next_follow_up_at: str | None = None
    follow_up_owner_id: uuid.UUID | None = None
    mark_contacted: bool | None = None
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


def _authorize_load_access(*, item: Any, token_payload: dict[str, Any]) -> None:
    token_org_id = token_payload.get("organization_id")
    if str(getattr(item, "organization_id", "")) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")

    token_role = str(token_payload.get("role") or "").lower()
    if token_role == "driver":
        token_driver_id = token_payload.get("driver_id")
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(getattr(item, "driver_id", "")) != str(token_driver_id):
            raise UnauthorizedError("Driver may only access own loads")


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




def _build_load_packet_readiness(item: Any) -> dict[str, Any]:
    documents = getattr(item, "documents", None)

    document_types = []
    if isinstance(documents, list):
        for document in documents:
            document_type = getattr(document, "document_type", None)
            if document_type is not None:
                document_types.append(document_type)

    if not document_types:
        if bool(getattr(item, "has_ratecon", False)):
            document_types.append(DocumentType.RATE_CONFIRMATION)
        if bool(getattr(item, "has_bol", False)):
            document_types.append(DocumentType.BILL_OF_LADING)
        if bool(getattr(item, "has_invoice", False)):
            document_types.append(DocumentType.INVOICE)

    return calculate_packet_readiness(document_types=document_types)

def _serialize_load(item: Any, *, detailed: bool = False) -> dict[str, Any]:
    customer_account = getattr(item, "customer_account", None)
    driver = getattr(item, "driver", None)
    broker = getattr(item, "broker", None)
    workflow_events = getattr(item, "workflow_events", None)
    validation_issues = getattr(item, "validation_issues", None)
    documents = getattr(item, "documents", None)
    last_reviewed_by_user = getattr(item, "last_reviewed_by_user", None)

    packet_readiness = _build_load_packet_readiness(item)
    operational = OperationalQueueService().evaluate_load(item)

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
        "packet_readiness": packet_readiness,
        "operational": operational,
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
                "last_contacted_at": _to_iso_or_none(getattr(item, "last_contacted_at", None)),
                "follow_up_required": bool(getattr(item, "follow_up_required", False)),
                "next_follow_up_at": _to_iso_or_none(getattr(item, "next_follow_up_at", None)),
                "follow_up_owner_id": _uuid_to_str(getattr(item, "follow_up_owner_id", None)),
                "follow_up_owner_name": (
                    getattr(getattr(item, "follow_up_owner", None), "full_name", None)
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


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_invoice_pdf(*, load: Any) -> bytes:
    customer_account = getattr(load, "customer_account", None)
    customer_display_name = (
        getattr(customer_account, "account_name", None)
        or getattr(load, "customer_account_id", None)
        or "N/A"
    )
    lines = [
        "Freight Back Office OS Invoice",
        "",
        f"Load Number: {load.load_number or 'N/A'}",
        f"Load ID: {load.id}",
        f"Customer: {customer_display_name}",
        f"Amount: {load.gross_amount or '0.00'} {load.currency_code or 'USD'}",
        f"Pickup: {load.pickup_location or 'N/A'} ({load.pickup_date or 'N/A'})",
        f"Delivery: {load.delivery_location or 'N/A'} ({load.delivery_date or 'N/A'})",
        f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]

    text_ops = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
    first_line = True
    for raw_line in lines:
        if first_line:
            text_ops.append(f"({_escape_pdf_text(raw_line)}) Tj")
            first_line = False
        else:
            text_ops.append("T*")
            text_ops.append(f"({_escape_pdf_text(raw_line)}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_position}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _generate_and_persist_invoice_pdf(*, db: Session, load: Any) -> bytes:
    pdf_bytes = _build_simple_invoice_pdf(load=load)
    storage_service = StorageService()
    document_service = DocumentService(db)

    existing_invoice_documents, _ = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=10,
    )

    if existing_invoice_documents:
        invoice_document = existing_invoice_documents[0]
        storage_key = getattr(invoice_document, "storage_key", None)
        if storage_key:
            storage_service.save_bytes(
                relative_path=str(storage_key),
                content=pdf_bytes,
                overwrite=True,
            )
        else:
            generated_storage_key = storage_service.save_bytes(
                relative_path=f"pdfs/generated-invoices/{uuid.uuid4().hex}.pdf",
                content=pdf_bytes,
                overwrite=False,
            )
            invoice_document.storage_key = generated_storage_key
            invoice_document.mime_type = "application/pdf"
            invoice_document.file_size_bytes = len(pdf_bytes)
            invoice_document.original_filename = f"invoice-{load.load_number or load.id}.pdf"
            document_service.document_repo.update(invoice_document)

        if str(getattr(invoice_document, "load_id", "")) != str(load.id):
            document_service.attach_to_load(
                document_id=str(invoice_document.id),
                load_id=str(load.id),
            )
        return pdf_bytes

    storage_key = storage_service.save_bytes(
        relative_path=f"pdfs/generated-invoices/{uuid.uuid4().hex}.pdf",
        content=pdf_bytes,
        overwrite=False,
    )
    document_service.create_document(
        organization_id=str(load.organization_id),
        customer_account_id=str(load.customer_account_id),
        driver_id=str(load.driver_id) if getattr(load, "driver_id", None) else None,
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        source_channel=getattr(load, "source_channel", "manual"),
        storage_key=storage_key,
        original_filename=f"invoice-{load.load_number or load.id}.pdf",
        mime_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
    )

    return pdf_bytes


@router.post("/loads", response_model=ApiResponse)
def create_load(
    payload: LoadCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")
    normalized_load_number = _normalize_optional_text(payload.load_number)
    normalized_broker_id = _uuid_to_str(payload.broker_id)
    normalized_broker_name = _normalize_optional_text(payload.broker_name_raw)
    normalized_broker_email = _normalize_email(payload.broker_email_raw)

    if not normalized_load_number:
        raise ValidationError("Load number is required", details={"load_number": payload.load_number})

    if not normalized_broker_id and not normalized_broker_name and not normalized_broker_email:
        raise ValidationError(
            "Broker selection or broker contact is required",
            details={
                "broker_id": payload.broker_id,
                "broker_name_raw": payload.broker_name_raw,
                "broker_email_raw": payload.broker_email_raw,
            },
        )

    service = LoadService(db)
    item = service.create_load(
        organization_id=str(payload.organization_id),
        customer_account_id=str(payload.customer_account_id),
        driver_id=str(payload.driver_id),
        broker_id=normalized_broker_id,
        source_channel=_normalize_required_text(payload.source_channel, "source_channel"),
        load_number=normalized_load_number,
        rate_confirmation_number=_normalize_optional_text(payload.rate_confirmation_number),
        bol_number=_normalize_optional_text(payload.bol_number),
        invoice_number=_normalize_optional_text(payload.invoice_number),
        broker_name_raw=normalized_broker_name,
        broker_email_raw=normalized_broker_email,
        pickup_date=_normalize_optional_text(payload.pickup_date),
        delivery_date=_normalize_optional_text(payload.delivery_date),
        pickup_location=_normalize_optional_text(payload.pickup_location),
        delivery_location=_normalize_optional_text(payload.delivery_location),
        gross_amount=_parse_decimal(payload.gross_amount, "gross_amount"),
        currency_code=_normalize_currency_code(payload.currency_code) or "USD",
        notes=_normalize_optional_text(payload.notes),
    )

    db.commit()
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
    queue: str | None = None,
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
    normalized_queue = _normalize_optional_text(queue)

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

    if normalized_queue:
        # Queue filtering is derived from operational state and done in-memory to avoid
        # duplicating business logic in the repository layer.
        all_items, _ = service.list_loads(
            organization_id=_uuid_to_str(effective_org_id),
            customer_account_id=_uuid_to_str(customer_account_id),
            driver_id=_uuid_to_str(effective_driver_id),
            status=_normalize_optional_text(status),
            source_channel=_normalize_optional_text(source_channel),
            date_from=_normalize_optional_text(date_from),
            date_to=_normalize_optional_text(date_to),
            search=_normalize_optional_text(search),
            page=1,
            page_size=500,
        )
        queue_service = OperationalQueueService()
        queue_filtered = [
            item
            for item in all_items
            if queue_service.evaluate_load(item).get("queue") == normalized_queue
        ]
        total = len(queue_filtered)
        start = (page - 1) * page_size
        end = start + page_size
        items = queue_filtered[start:end]

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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    item = service.get_load(str(load_id))
    _authorize_load_access(item=item, token_payload=token_payload)

    return ApiResponse(
        data=_serialize_load(item, detailed=True),
        meta={},
        error=None,
    )


@router.patch("/loads/{load_id}", response_model=ApiResponse)
def update_load(
    load_id: uuid.UUID,
    payload: LoadUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    existing = service.get_load(str(load_id))
    token_org_id = token_payload.get("organization_id")
    if str(existing.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")

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
        follow_up_required=payload.follow_up_required,
        next_follow_up_at=_normalize_optional_text(payload.next_follow_up_at),
        follow_up_owner_id=_uuid_to_str(payload.follow_up_owner_id),
        last_contacted_at=datetime.now(timezone.utc) if payload.mark_contacted else None,
        notes=_normalize_optional_text(payload.notes),
    )

    db.commit()
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    existing = service.get_load(str(load_id))
    token_org_id = token_payload.get("organization_id")
    if str(existing.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")

    parsed_status = _parse_load_status(payload.new_status)

    engine = WorkflowEngine(db)
    result = engine.transition_load(
        load_id=str(load_id),
        new_status=parsed_status,
        actor_staff_user_id=_uuid_to_str(payload.actor_staff_user_id),
        actor_type=_normalize_required_text(payload.actor_type, "actor_type"),
        notes=_normalize_optional_text(payload.notes),
    )

    db.commit()

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


@router.post("/loads/{load_id}/workflow-actions", response_model=ApiResponse)
def execute_load_workflow_action(
    load_id: uuid.UUID,
    payload: LoadWorkflowActionRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = LoadService(db)
    existing = service.get_load(str(load_id))
    token_org_id = token_payload.get("organization_id")
    if str(existing.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")

    engine = WorkflowEngine(db)
    result = engine.apply_operational_action(
        load_id=str(load_id),
        action=_normalize_required_text(payload.action, "action"),
        actor_staff_user_id=_uuid_to_str(payload.actor_staff_user_id),
        actor_type=_normalize_required_text(payload.actor_type, "actor_type"),
        follow_up_required=payload.follow_up_required,
        next_follow_up_at=_normalize_optional_text(payload.next_follow_up_at),
        follow_up_owner_id=_uuid_to_str(payload.follow_up_owner_id),
        notes=_normalize_optional_text(payload.notes),
    )
    db.commit()

    return ApiResponse(
        data={
            "id": result["id"],
            "old_status": result["old_status"],
            "new_status": result["new_status"],
            "changed_at": result["changed_at"],
            "action": _normalize_required_text(payload.action, "action").lower(),
        },
        meta={},
        error=None,
    )


@router.get("/loads/{load_id}/invoice")
def download_load_invoice(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)
    pdf_bytes = _generate_and_persist_invoice_pdf(db=db, load=load)
    filename = f"invoice-{load.load_number or load.id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
