from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.dependencies import get_db_session
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.domain.enums.document_type import DocumentType
from app.domain.enums.follow_up_task import FollowUpTaskStatus, FollowUpTaskType
from app.domain.enums.load_status import LoadStatus
from app.domain.models.follow_up_task import FollowUpTask
from app.schemas.common import ApiResponse
from app.services.audit.audit_service import AuditService
from app.services.carrier_profile_service import CarrierProfileService
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.email.email_service import PacketEmailService
from app.services.loads.load_service import LoadService
from app.services.loads.operational_queue_service import OperationalQueueService
from app.services.loads.packet_readiness import calculate_packet_readiness
from app.services.loads.submission_packet_service import SubmissionPacketService
from app.services.notifications.operational_notification_service import (
    OperationalNotificationService,
)
from app.services.packet_intelligence.packet_audit_service import PacketAuditService
from app.services.workflow.workflow_engine import WorkflowEngine
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)

router = APIRouter()
logger = logging.getLogger(__name__)


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


class DriverLoadCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    eta_note: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy_meters: float | None = None


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


def _log_load_activity(
    *,
    db: Session,
    organization_id: object,
    entity_type: str,
    entity_id: object,
    action: str,
    token_payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    actor_id = (
        str(token_payload.get("staff_user_id") or token_payload.get("sub") or "").strip() or None
    )
    AuditService(db).log_event(
        organization_id=str(organization_id),
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_id=actor_id,
        actor_type="staff_user" if actor_id else "system",
        metadata_json=metadata or {},
    )


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


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_packet_recipient_email(value: str | None, field_name: str = "to_email") -> str:
    normalized = _normalize_required_text(value or "", field_name).lower()
    if not _EMAIL_PATTERN.match(normalized):
        raise ValidationError("Enter a valid recipient email.", details={field_name: value})
    return normalized


def _sanitize_packet_send_result(send_result: dict[str, Any]) -> dict[str, Any]:
    status = "sent" if bool(send_result.get("accepted")) else "failed"
    error_message = _normalize_optional_text(str(send_result.get("error_message") or ""))
    if error_message and "disabled" in error_message.lower():
        status = "skipped"
    return {
        "provider": send_result.get("provider") or "none",
        "accepted": bool(send_result.get("accepted")),
        "status": status,
        "provider_message_id": send_result.get("provider_message_id"),
        "error_message": error_message,
    }


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


def _build_load_packet_readiness(item: Any, *, db: Session | None = None) -> dict[str, Any]:
    documents = getattr(item, "documents", None)

    document_types = []
    if isinstance(documents, list):
        for document in documents:
            document_type = getattr(document, "document_type", None)
            if document_type is not None:
                document_types.append(document_type)

    readiness_source = "load.documents"
    if not document_types and db is not None and getattr(item, "id", None):
        document_service = DocumentService(db)
        persisted_documents, _ = document_service.list_documents(
            load_id=str(item.id),
            page=1,
            page_size=500,
        )
        for document in persisted_documents:
            document_type = getattr(document, "document_type", None)
            if document_type is not None:
                document_types.append(document_type)
        readiness_source = "documents_table"

    logger.debug(
        "Load packet readiness input: load_id=%s source=%s document_types=%s",
        getattr(item, "id", None),
        readiness_source,
        [getattr(document_type, "value", str(document_type)) for document_type in document_types],
    )

    return calculate_packet_readiness(document_types=document_types)


class SubmissionPacketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None


class SubmissionPacketMarkSentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination_type: str
    destination_name: str | None = None
    destination_email: str | None = None
    notes: str | None = None


class SubmissionPacketMarkRejectedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str
    resubmission_required: bool = False


class SubmissionPacketSendEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_email: str
    cc: list[str] | None = None
    bcc: list[str] | None = None
    subject: str | None = None
    body: str | None = None


def _authorize_submission_read(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").lower()
    if role == "driver":
        raise ForbiddenError("Drivers cannot access submission packets")


def _authorize_submission_write(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").lower()
    if role in {"driver", "viewer", "support_agent", "support"}:
        raise ForbiddenError("You do not have permission to modify submission packets")


def _authorize_submission_download(*, item: Any, token_payload: dict[str, Any]) -> None:
    token_org_id = token_payload.get("organization_id")
    if str(getattr(item, "organization_id", "")) != str(token_org_id):
        raise ForbiddenError("Load is not in authenticated organization")

    role = str(token_payload.get("role") or "").lower()
    if role not in {"owner", "admin", "ops", "billing"}:
        raise ForbiddenError("You do not have permission to download submission packets")


def _serialize_packet_audit(audit: Any) -> dict[str, Any] | None:
    if audit is None:
        return None
    if hasattr(audit, "to_dict"):
        return audit.to_dict()
    if isinstance(audit, dict):
        return audit
    return None


def _serialize_submission_packet(packet: Any) -> dict[str, Any]:
    loaded_values = getattr(packet, "__dict__", {})
    packet_documents = loaded_values.get("documents") or []
    packet_events = loaded_values.get("events") or []
    return {
        "id": _uuid_to_str(getattr(packet, "id", None)),
        "organization_id": _uuid_to_str(getattr(packet, "organization_id", None)),
        "load_id": _uuid_to_str(getattr(packet, "load_id", None)),
        "packet_reference": getattr(packet, "packet_reference", None),
        "destination_type": getattr(packet, "destination_type", None),
        "destination_name": getattr(packet, "destination_name", None),
        "destination_email": getattr(packet, "destination_email", None),
        "status": getattr(packet, "status", None),
        "notes": getattr(packet, "notes", None),
        "created_by_staff_user_id": _uuid_to_str(getattr(packet, "created_by_staff_user_id", None)),
        "sent_by_staff_user_id": _uuid_to_str(getattr(packet, "sent_by_staff_user_id", None)),
        "sent_at": _to_iso_or_none(getattr(packet, "sent_at", None)),
        "accepted_at": _to_iso_or_none(getattr(packet, "accepted_at", None)),
        "rejected_at": _to_iso_or_none(getattr(packet, "rejected_at", None)),
        "created_at": _to_iso_or_none(getattr(packet, "created_at", None)),
        "updated_at": _to_iso_or_none(getattr(packet, "updated_at", None)),
        "packet_audit": _serialize_packet_audit(getattr(packet, "packet_audit", None)),
        "documents": [
            {
                "id": _uuid_to_str(getattr(doc, "id", None)),
                "document_id": _uuid_to_str(getattr(doc, "document_id", None)),
                "document_type": getattr(doc, "document_type", None),
                "filename_snapshot": getattr(doc, "filename_snapshot", None),
                "created_at": _to_iso_or_none(getattr(doc, "created_at", None)),
            }
            for doc in packet_documents
        ],
        "events": [
            {
                "id": _uuid_to_str(getattr(event, "id", None)),
                "event_type": getattr(event, "event_type", None),
                "message": getattr(event, "message", None),
                "created_by_staff_user_id": _uuid_to_str(
                    getattr(event, "created_by_staff_user_id", None)
                ),
                "created_at": _to_iso_or_none(getattr(event, "created_at", None)),
            }
            for event in sorted(
                packet_events,
                key=lambda item: getattr(item, "created_at", datetime.min),
            )
        ],
    }


def _serialize_packet_email_history(packet: Any) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    event_priority = {
        "packet_email_sent": 3,
        "packet_email_failed": 3,
        "packet_email_send_attempt": 1,
    }
    for event in sorted(
        (getattr(packet, "events", None) or []),
        key=lambda item: (
            getattr(item, "created_at", datetime.min),
            event_priority.get(str(getattr(item, "event_type", "")), 0),
        ),
        reverse=True,
    ):
        event_type = getattr(event, "event_type", None)
        if not str(event_type or "").startswith("packet_email_"):
            continue
        message = getattr(event, "message", None) or ""
        recipient_match = re.search(r"(?:to|for) ([^;:\s]+@[^;:\s]+)", message)
        subject_match = re.search(r"subject=([^;]+)", message)
        attachment_match = re.search(r"attachments=(\d+)", message)
        if event_type == "packet_email_sent":
            status = "sent"
        elif event_type == "packet_email_failed":
            status = (
                "skipped"
                if "skipped" in message.lower() or "disabled" in message.lower()
                else "failed"
            )
        elif event_type == "packet_email_send_attempt":
            status = "queued"
        else:
            status = str(event_type).replace("packet_email_", "")
        history.append(
            {
                "id": _uuid_to_str(getattr(event, "id", None)),
                "status": status,
                "recipient": recipient_match.group(1)
                if recipient_match
                else getattr(packet, "destination_email", None),
                "subject": subject_match.group(1).strip() if subject_match else None,
                "sent_at": _to_iso_or_none(getattr(event, "created_at", None)),
                "sent_by_staff_user_id": _uuid_to_str(
                    getattr(event, "created_by_staff_user_id", None)
                ),
                "attachment_count": int(attachment_match.group(1)) if attachment_match else None,
                "message": "Packet email status recorded."
                if status in {"failed", "skipped"}
                else message,
            }
        )
    return history


def _build_default_packet_email(
    *, packet: Any, load: Any, carrier_name: str | None = None
) -> tuple[str, str]:
    load_number = _string_or_na(getattr(load, "load_number", None))
    invoice_number = _string_or_na(getattr(load, "invoice_number", None))
    amount = (
        f"{_string_or_na(getattr(load, 'gross_amount', None))} "
        f"{_string_or_na(getattr(load, 'currency_code', None))}"
    )
    subject = f"Billing Packet | Load {load_number} | Invoice {invoice_number}"
    sender_name = carrier_name or "Carrier"
    body = "\n".join(
        [
            "Hello,",
            "",
            f"Attached is the billing packet for Load {load_number} and Invoice {invoice_number}.",
            "",
            "Included documents:",
            "- Invoice",
            "- Rate Confirmation",
            "- Proof of Delivery",
            "- Bill of Lading (if available)",
            "",
            f"Carrier: {sender_name}",
            f"Invoice Number: {invoice_number}",
            f"Invoice Amount: {amount}",
            f"Pickup: {_string_or_na(getattr(load, 'pickup_location', None))}",
            f"Delivery: {_string_or_na(getattr(load, 'delivery_location', None))}",
            "",
            (
                "Please confirm receipt and advise if any additional documentation is required. "
                "Payment/remit instructions are included with the invoice or "
                "carrier profile on file."
            ),
            "",
            "Thank you,",
            sender_name,
        ]
    )
    return subject, body


def _serialize_load(
    item: Any, *, detailed: bool = False, db: Session | None = None
) -> dict[str, Any]:
    customer_account = getattr(item, "customer_account", None)
    driver = getattr(item, "driver", None)
    broker = getattr(item, "broker", None)
    workflow_events = getattr(item, "workflow_events", None)
    validation_issues = getattr(item, "validation_issues", None)
    documents = getattr(item, "documents", None)
    last_reviewed_by_user = getattr(item, "last_reviewed_by_user", None)

    packet_readiness = _build_load_packet_readiness(item, db=db)
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
                "extraction_confidence_avg": _to_decimal_string(item.extraction_confidence_avg),
                "last_reviewed_by": (
                    str(item.last_reviewed_by) if getattr(item, "last_reviewed_by", None) else None
                ),
                "last_reviewed_by_name": (
                    getattr(last_reviewed_by_user, "full_name", None)
                    if last_reviewed_by_user
                    else None
                ),
                "last_reviewed_at": _to_iso_or_none(getattr(item, "last_reviewed_at", None)),
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


def _format_invoice_date(value: object | None) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            iso_value = isoformat()
            return str(iso_value)[:10]
        except Exception:  # pragma: no cover - defensive fallback for unknown objects
            return str(value)
    return str(value)


def _string_or_na(value: object | None) -> str:
    if value is None:
        return "N/A"
    normalized = str(value).strip()
    return normalized or "N/A"


def _format_money(value: object | None) -> str:
    if value is None:
        return "0.00"
    try:
        return f"{Decimal(str(value)).quantize(Decimal('0.01')):,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _pdf_checkbox_label(label: str, *, checked: bool) -> str:
    return f"[{'X' if checked else ' '}] {label}"


def _build_carrier_profile_context(*, db: Session, load: Any) -> dict[str, str]:
    profile = CarrierProfileService(db).get_by_org(getattr(load, "organization_id", None))
    action_url = "/dashboard/settings/carrier-profile"
    if profile is None:
        raise ValidationError(
            "Complete Carrier Profile before generating invoice",
            details={
                "organization_id": str(getattr(load, "organization_id", "")),
                "code": "carrier_profile_incomplete",
                "missing_fields": [
                    "address_line1",
                    "city",
                    "state",
                    "postal_code",
                    "phone",
                    "email",
                    "remit_to_name",
                    "remit_to_address",
                ],
                "action_url": action_url,
            },
        )

    missing_fields: list[str] = []
    required_fields = {
        "address_line1": profile.address_line1,
        "city": profile.city,
        "state": profile.state,
        "postal_code": profile.zip,
        "phone": profile.phone,
        "email": profile.email,
        "remit_to_name": profile.remit_to_name,
        "remit_to_address": profile.remit_to_address,
    }
    for field, value in required_fields.items():
        if value is None or not str(value).strip():
            missing_fields.append(field)
    if missing_fields:
        raise ValidationError(
            "Complete Carrier Profile before generating invoice.",
            details={
                "organization_id": str(getattr(load, "organization_id", "")),
                "code": "carrier_profile_incomplete",
                "missing_fields": missing_fields,
                "action_url": action_url,
            },
        )

    address_parts = [
        profile.address_line1,
        profile.address_line2,
        f"{profile.city}, {profile.state} {profile.zip}",
        profile.country,
    ]
    remit_parts = [profile.remit_to_name, profile.remit_to_address, profile.remit_to_notes]

    return {
        "legal_name": profile.legal_name,
        "email": profile.email,
        "phone": profile.phone,
        "mc_number": _string_or_na(profile.mc_number),
        "dot_number": _string_or_na(profile.dot_number),
        "address": " | ".join([part for part in address_parts if part]),
        "remit_to": " | ".join([part for part in remit_parts if part]),
    }


def _ensure_load_invoice_number(*, db: Session, load: Any) -> str:
    existing = _normalize_optional_text(getattr(load, "invoice_number", None))
    if existing:
        return existing

    year = datetime.utcnow().year
    org_id = str(load.organization_id)
    prefix = f"INV-{year}-"

    loads, _ = LoadService(db).list_loads(organization_id=org_id, page=1, page_size=5000)
    max_increment = 0
    for item in loads:
        number = _normalize_optional_text(getattr(item, "invoice_number", None))
        if not number or not number.startswith(prefix):
            continue
        tail = number.removeprefix(prefix)
        if tail.isdigit():
            max_increment = max(max_increment, int(tail))

    invoice_number = f"{prefix}{(max_increment + 1):05d}"
    load.invoice_number = invoice_number
    db.add(load)
    db.flush()
    return invoice_number


def _build_professional_invoice_pdf(*, load: Any, carrier_profile: dict[str, str]) -> bytes:
    organization = getattr(load, "organization", None)
    customer_account = getattr(load, "customer_account", None)
    broker = getattr(load, "broker", None)
    driver = getattr(load, "driver", None)
    documents = getattr(load, "documents", None) or []

    present_document_values = {
        getattr(
            getattr(document, "document_type", None),
            "value",
            str(getattr(document, "document_type", "")),
        )
        for document in documents
        if getattr(document, "document_type", None) is not None
    }

    invoice_number = _string_or_na(getattr(load, "invoice_number", None))
    invoice_date_value = datetime.utcnow().date()
    invoice_date = _format_invoice_date(invoice_date_value)
    load_number = _string_or_na(getattr(load, "load_number", None))
    load_reference = _string_or_na(getattr(load, "load_number", None))
    if load_reference == "N/A":
        load_reference = _string_or_na(getattr(load, "rate_confirmation_number", None))
    if load_reference == "N/A":
        load_reference = str(getattr(load, "id", "N/A"))

    carrier_name = carrier_profile["legal_name"]
    company_name = _string_or_na(getattr(organization, "name", None))
    display_brand_name = carrier_name if carrier_name != "N/A" else company_name
    carrier_email = carrier_profile["email"]
    carrier_phone = carrier_profile["phone"]
    carrier_address = carrier_profile["address"]
    carrier_mc_number = carrier_profile["mc_number"]
    carrier_dot_number = carrier_profile["dot_number"]
    remit_to_instructions = carrier_profile["remit_to"]

    customer_name = (
        _string_or_na(getattr(customer_account, "account_name", None))
        if customer_account is not None
        else _string_or_na(getattr(load, "customer_account_id", None))
    )
    billing_email = _string_or_na(getattr(customer_account, "billing_email", None))

    broker_name = _string_or_na(getattr(broker, "name", None))
    if broker_name == "N/A":
        broker_name = _string_or_na(getattr(load, "broker_name_raw", None))
    broker_email = _string_or_na(getattr(broker, "email", None))
    if broker_email == "N/A":
        broker_email = _string_or_na(getattr(load, "broker_email_raw", None))
    broker_mc_number = _string_or_na(getattr(broker, "mc_number", None))
    payment_terms_days = getattr(broker, "payment_terms_days", None)
    payment_terms = f"Net {payment_terms_days} days" if payment_terms_days is not None else "N/A"
    due_date = (
        _format_invoice_date(invoice_date_value + timedelta(days=int(payment_terms_days)))
        if isinstance(payment_terms_days, int) and payment_terms_days >= 0
        else "Not provided"
    )

    pickup_date = _format_invoice_date(getattr(load, "pickup_date", None))
    delivery_date = _format_invoice_date(getattr(load, "delivery_date", None))
    gross_amount = _format_money(getattr(load, "gross_amount", None))
    currency_code = _string_or_na(getattr(load, "currency_code", None))
    total_due = f"{gross_amount} {currency_code}"

    text_ops: list[str] = ["0.6 w", "0 0 0 RG"]
    line_gap = 11

    def add_text(x: int, y: int, text: str, *, font: str = "F1", size: int = 9) -> None:
        escaped = _escape_pdf_text(text)
        text_ops.extend(["BT", f"/{font} {size} Tf", f"{x} {y} Td", f"({escaped}) Tj", "ET"])

    def add_box(x: int, y: int, width: int, height: int) -> None:
        text_ops.append("0.72 0.76 0.82 RG")
        text_ops.append(f"{x} {y} {width} {height} re S")
        text_ops.append("0 0 0 RG")

    def add_filled_box(
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        fill: str = "0.95 0.97 0.99 rg",
        stroke: str = "0.72 0.76 0.82 RG",
    ) -> None:
        text_ops.extend([fill, stroke, f"{x} {y} {width} {height} re B", "0 0 0 rg", "0 0 0 RG"])

    def add_rule(x1: int, y: int, x2: int) -> None:
        text_ops.append("0.78 0.81 0.86 RG")
        text_ops.append(f"{x1} {y} m {x2} {y} l S")
        text_ops.append("0 0 0 RG")

    def _safe_text(value: object | None, *, missing: str = "Not provided") -> str:
        normalized = _normalize_optional_text(value)
        if normalized is None or normalized == "N/A":
            return missing
        return normalized

    def _wrap_text(value: str, *, max_chars: int, max_lines: int | None = None) -> list[str]:
        normalized = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        if not normalized or normalized == "N/A":
            normalized = "Not provided"

        words = normalized.split()
        lines: list[str] = []
        current_line = ""

        for word in words:
            proposed = f"{current_line} {word}".strip()
            if len(proposed) <= max_chars:
                current_line = proposed
                continue

            if current_line:
                lines.append(current_line)
                current_line = ""

            while len(word) > max_chars:
                lines.append(word[: max_chars - 1] + "-")
                word = word[max_chars - 1 :]

            current_line = word

        if current_line:
            lines.append(current_line)

        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines and len(lines[-1]) >= max_chars - 2:
                lines[-1] = lines[-1][: max_chars - 3].rstrip() + "..."
            elif lines:
                lines[-1] = lines[-1].rstrip() + "..."

        return lines or ["Not provided"]

    def add_wrapped_field(
        *,
        x: int,
        y: int,
        label: str,
        value: str,
        max_chars: int,
        max_lines: int,
        label_width: int = 74,
    ) -> int:
        wrapped_lines = _wrap_text(value, max_chars=max_chars, max_lines=max_lines)
        add_text(x, y, f"{label}: {wrapped_lines[0]}", font="F2", size=8)
        y_cursor = y - line_gap
        continuation_x = x + min(label_width, 86)
        for line in wrapped_lines[1:]:
            add_text(continuation_x, y_cursor, line, size=8)
            y_cursor -= line_gap
        return y_cursor

    def brand_initials(name: str) -> str:
        words = [part[0].upper() for part in re.findall(r"[A-Za-z0-9]+", name)[:3] if part]
        return "".join(words) or "FB"

    # Header with safe text-based branding fallback. Image logo embedding is skipped until
    # a carrier logo field exists; missing logos never affect PDF generation.
    add_filled_box(36, 692, 540, 76, fill="0.92 0.95 0.99 rg")
    add_filled_box(50, 724, 42, 28, fill="0.12 0.24 0.42 rg", stroke="0.12 0.24 0.42 RG")
    add_text(59, 734, brand_initials(display_brand_name), font="F2", size=11)
    add_text(104, 746, _safe_text(display_brand_name), font="F2", size=13)
    add_wrapped_field(x=104, y=728, label="Carrier", value=carrier_name, max_chars=43, max_lines=1)
    add_text(432, 746, "Freight Invoice", font="F2", size=15)
    add_text(432, 729, f"Invoice #: {invoice_number}", font="F2", size=9)
    add_text(432, 716, f"Invoice Date: {invoice_date}", size=8)
    add_text(432, 703, f"Due Date: {due_date}", size=8)

    # Carrier / Bill-to sections
    left_x = 36
    right_x = 316
    section_y = 512
    section_h = 168
    section_w = 260
    add_box(left_x, section_y, section_w, section_h)
    add_box(right_x, section_y, section_w, section_h)
    add_filled_box(left_x, section_y + section_h - 28, section_w, 28)
    add_filled_box(right_x, section_y + section_h - 28, section_w, 28)
    add_text(left_x + 14, section_y + section_h - 18, "Carrier / Remit-To", font="F2", size=10)
    add_text(right_x + 14, section_y + section_h - 18, "Bill-To / Broker", font="F2", size=10)

    left_cursor = section_y + section_h - 42
    left_cursor = add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="Carrier",
        value=carrier_name,
        max_chars=30,
        max_lines=2,
    )
    left_cursor = add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="Address",
        value=_safe_text(carrier_address),
        max_chars=30,
        max_lines=3,
    )
    left_cursor = add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="Phone",
        value=_safe_text(carrier_phone),
        max_chars=31,
        max_lines=1,
    )
    left_cursor = add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="Email",
        value=_safe_text(carrier_email),
        max_chars=31,
        max_lines=1,
    )
    left_cursor = add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="MC",
        value=_safe_text(carrier_mc_number),
        max_chars=31,
        max_lines=1,
    )
    add_wrapped_field(
        x=left_x + 14,
        y=left_cursor,
        label="DOT",
        value=_safe_text(carrier_dot_number),
        max_chars=31,
        max_lines=1,
    )

    right_cursor = section_y + section_h - 42
    right_cursor = add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Customer",
        value=_safe_text(customer_name),
        max_chars=29,
        max_lines=2,
    )
    right_cursor = add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Billing Email",
        value=_safe_text(billing_email),
        max_chars=29,
        max_lines=2,
    )
    right_cursor = add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Broker",
        value=_safe_text(broker_name),
        max_chars=29,
        max_lines=2,
    )
    right_cursor = add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Broker Email",
        value=_safe_text(broker_email),
        max_chars=29,
        max_lines=1,
    )
    right_cursor = add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Broker MC",
        value=_safe_text(broker_mc_number),
        max_chars=29,
        max_lines=1,
    )
    add_wrapped_field(
        x=right_x + 14,
        y=right_cursor,
        label="Terms",
        value=_safe_text(payment_terms),
        max_chars=29,
        max_lines=1,
    )

    # Shipment details
    add_box(36, 390, 540, 108)
    add_filled_box(36, 470, 540, 28)
    add_text(50, 480, "Shipment Details", font="F2", size=10)
    add_wrapped_field(
        x=50,
        y=454,
        label="Load #",
        value=load_number,
        max_chars=33,
        max_lines=1,
    )
    add_wrapped_field(
        x=50,
        y=438,
        label="Pickup",
        value=_safe_text(getattr(load, "pickup_location", None)),
        max_chars=33,
        max_lines=2,
    )
    add_text(50, 410, f"Pickup Date: {_safe_text(pickup_date)}", font="F2", size=8)
    add_wrapped_field(
        x=304,
        y=454,
        label="Load Ref",
        value=load_reference,
        max_chars=30,
        max_lines=2,
    )
    add_wrapped_field(
        x=304,
        y=430,
        label="Delivery",
        value=_safe_text(getattr(load, "delivery_location", None)),
        max_chars=30,
        max_lines=2,
    )
    add_text(304, 402, f"Delivery Date: {_safe_text(delivery_date)}", font="F2", size=8)
    add_wrapped_field(
        x=50,
        y=395,
        label="Driver",
        value=_safe_text(getattr(driver, "full_name", None)),
        max_chars=76,
        max_lines=1,
    )
    add_wrapped_field(
        x=304,
        y=395,
        label="Notes",
        value=_safe_text(getattr(load, "notes", None)),
        max_chars=30,
        max_lines=1,
    )

    # Charges / totals
    add_box(36, 272, 540, 104)
    add_filled_box(36, 348, 540, 28)
    add_text(50, 358, "Charges", font="F2", size=10)
    add_text(50, 332, "Description", font="F2", size=8)
    add_text(380, 332, "Amount", font="F2", size=8)
    add_text(470, 332, "Currency", font="F2", size=8)
    add_rule(50, 324, 562)
    add_text(50, 309, "Linehaul / Freight Charge", size=9)
    add_text(380, 309, gross_amount, size=9)
    add_text(470, 309, currency_code, size=9)
    add_rule(50, 296, 562)
    add_filled_box(360, 278, 202, 40, fill="0.90 0.95 0.91 rg", stroke="0.42 0.62 0.44 RG")
    add_text(374, 302, "Total Due", font="F2", size=11)
    add_text(446, 290, total_due, font="F2", size=13)
    add_text(50, 284, f"Payment Terms: {_safe_text(payment_terms)}", size=8)

    # Checklist
    checklist_y = 164
    checklist_h = 94
    add_box(36, checklist_y, 540, checklist_h)
    add_filled_box(36, checklist_y + checklist_h - 28, 540, 28)
    add_text(
        50,
        checklist_y + checklist_h - 18,
        "Required Billing Packet Checklist",
        font="F2",
        size=10,
    )

    required_items = [
        _pdf_checkbox_label(
            "Rate Confirmation",
            checked=DocumentType.RATE_CONFIRMATION.value in present_document_values,
        ),
        _pdf_checkbox_label(
            "Bill of Lading",
            checked=DocumentType.BILL_OF_LADING.value in present_document_values,
        ),
        _pdf_checkbox_label(
            "Proof of Delivery",
            checked=DocumentType.PROOF_OF_DELIVERY.value in present_document_values,
        ),
        _pdf_checkbox_label("Invoice", checked=True),
    ]
    optional_items = [
        (
            "Lumper Receipt",
            DocumentType.LUMPER_RECEIPT.value in present_document_values,
        ),
        (
            "Scale Ticket",
            DocumentType.SCALE_TICKET.value in present_document_values,
        ),
        (
            "Detention Support",
            DocumentType.DETENTION_SUPPORT.value in present_document_values,
        ),
        (
            "Accessorial Support",
            DocumentType.ACCESSORIAL_SUPPORT.value in present_document_values,
        ),
    ]

    left_check_y = checklist_y + checklist_h - 46
    for item in required_items:
        add_text(50, left_check_y, item, size=8)
        left_check_y -= line_gap

    right_check_y = checklist_y + checklist_h - 46
    for label, is_present in optional_items:
        add_text(324, right_check_y, _pdf_checkbox_label(label, checked=is_present), size=8)
        right_check_y -= line_gap

    # Footer / remittance
    add_box(36, 56, 540, 94)
    add_filled_box(36, 122, 540, 28)
    add_text(50, 132, "Payment / Remittance", font="F2", size=10)
    add_wrapped_field(
        x=50,
        y=108,
        label="Remit Instructions",
        value=_safe_text(remit_to_instructions),
        max_chars=77,
        max_lines=3,
        label_width=86,
    )
    add_text(
        50, 72, "Please reference invoice number and load number with payment.", font="F2", size=9
    )
    add_text(50, 60, f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", size=8)

    stream = "\n".join(text_ops).encode("latin-1", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF"
        ).encode("ascii")
    )

    return bytes(pdf)


def _generate_and_persist_invoice_pdf(*, db: Session, load: Any) -> bytes:
    template_function_name = "_build_professional_invoice_pdf"
    logger.info(
        "USING TEMPLATE: %s for load_id=%s",
        template_function_name,
        getattr(load, "id", None),
    )
    carrier_profile = _build_carrier_profile_context(db=db, load=load)
    _ensure_load_invoice_number(db=db, load=load)
    pdf_bytes = _build_professional_invoice_pdf(load=load, carrier_profile=carrier_profile)
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

        document_service.attach_to_load(
            document_id=str(invoice_document.id),
            load_id=str(load.id),
        )
        logger.info(
            (
                "Generated invoice PDF reused existing document: "
                "load_id=%s document_id=%s document_type=%s"
            ),
            load.id,
            getattr(invoice_document, "id", None),
            getattr(getattr(invoice_document, "document_type", None), "value", None),
        )
        return pdf_bytes

    storage_key = storage_service.save_bytes(
        relative_path=f"pdfs/generated-invoices/{uuid.uuid4().hex}.pdf",
        content=pdf_bytes,
        overwrite=False,
    )
    invoice_document = document_service.create_document(
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
    logger.info(
        "Generated invoice PDF created document: load_id=%s document_id=%s document_type=%s",
        load.id,
        getattr(invoice_document, "id", None),
        getattr(getattr(invoice_document, "document_type", None), "value", None),
    )

    return pdf_bytes


def _assert_staff_load_management_role(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role == "driver":
        raise ForbiddenError("Driver accounts must use driver load endpoints")


@router.post("/loads", response_model=ApiResponse)
def create_load(
    payload: LoadCreateRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _assert_staff_load_management_role(token_payload)
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")
    normalized_load_number = _normalize_optional_text(payload.load_number)
    normalized_broker_id = _uuid_to_str(payload.broker_id)
    normalized_broker_name = _normalize_optional_text(payload.broker_name_raw)
    normalized_broker_email = _normalize_email(payload.broker_email_raw)

    if not normalized_load_number:
        raise ValidationError(
            "Load number is required", details={"load_number": payload.load_number}
        )

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
        data=_serialize_load(item, detailed=True, db=db),
        meta={},
        error=None,
    )


@router.get("/driver/loads", response_model=ApiResponse)
def list_driver_loads(
    *,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_role = str(token_payload.get("role") or "").lower()
    token_driver_id = token_payload.get("driver_id")
    token_org_id = token_payload.get("organization_id")

    if token_role != "driver":
        raise ForbiddenError("Only driver accounts can access driver loads")
    if not token_driver_id:
        raise UnauthorizedError("Driver token is missing driver_id")

    service = LoadService(db)
    items, total = service.list_loads(
        organization_id=str(token_org_id),
        driver_id=str(token_driver_id),
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=[_serialize_load(item, detailed=False, db=db) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/driver/loads/{load_id}", response_model=ApiResponse)
def get_driver_load(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_role = str(token_payload.get("role") or "").lower()
    if token_role != "driver":
        raise ForbiddenError("Only driver accounts can access driver loads")

    service = LoadService(db)
    item = service.get_load(str(load_id))
    _authorize_load_access(item=item, token_payload=token_payload)
    return ApiResponse(data=_serialize_load(item, detailed=True, db=db), meta={}, error=None)


@router.post("/driver/loads/{load_id}/check-in", response_model=ApiResponse)
def driver_load_check_in(
    load_id: uuid.UUID,
    payload: DriverLoadCheckInRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_role = str(token_payload.get("role") or "").lower()
    if token_role != "driver":
        raise ForbiddenError("Only driver accounts can update driver load check-ins")

    service = LoadService(db)
    existing = service.get_load(str(load_id))
    _authorize_load_access(item=existing, token_payload=token_payload)

    parsed_status = _parse_load_status(payload.status)
    if parsed_status not in {LoadStatus.IN_TRANSIT, LoadStatus.DELIVERED}:
        raise ValidationError(
            "Driver check-ins only support in_transit or delivered statuses",
            details={"status": payload.status},
        )

    notes_parts = [
        "Driver mobile check-in",
        f"status={parsed_status.value}",
    ]
    eta_note = _normalize_optional_text(payload.eta_note)
    if eta_note:
        notes_parts.append(f"eta={eta_note}")
    if payload.latitude is not None and payload.longitude is not None:
        accuracy = (
            round(payload.location_accuracy_meters, 1)
            if payload.location_accuracy_meters is not None
            else "unknown"
        )
        notes_parts.append(
            "location="
            f"{round(payload.latitude, 5)},{round(payload.longitude, 5)}"
            f" accuracy_m={accuracy}"
        )

    engine = WorkflowEngine(db)
    result = engine.transition_load(
        load_id=str(load_id),
        new_status=parsed_status,
        actor_staff_user_id=None,
        actor_type="driver",
        notes="; ".join(notes_parts),
    )
    transitioned_load = service.get_load(str(load_id))

    _log_load_activity(
        db=db,
        organization_id=transitioned_load.organization_id,
        entity_type="load",
        entity_id=transitioned_load.id,
        action="driver.mobile_check_in",
        token_payload=token_payload,
        metadata={
            "new_status": parsed_status.value,
            "eta_note_present": bool(eta_note),
            "location_present": payload.latitude is not None and payload.longitude is not None,
        },
    )
    db.commit()

    return ApiResponse(
        data=_serialize_load(transitioned_load, detailed=True, db=db),
        meta={"driver_check_in": True, "transition": result},
        error=None,
    )


@router.get("/loads", response_model=ApiResponse)
def list_loads(
    *,
    organization_id: uuid.UUID | None = None,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
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
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _assert_staff_load_management_role(token_payload)
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
        data=[_serialize_load(item, detailed=False, db=db) for item in items],
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    service = LoadService(db)
    item = service.get_load(str(load_id))
    _authorize_load_access(item=item, token_payload=token_payload)

    return ApiResponse(
        data=_serialize_load(item, detailed=True, db=db),
        meta={},
        error=None,
    )


@router.patch("/loads/{load_id}", response_model=ApiResponse)
def update_load(
    load_id: uuid.UUID,
    payload: LoadUpdateRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
        data=_serialize_load(item, detailed=True, db=db),
        meta={},
        error=None,
    )


@router.post("/loads/{load_id}/status", response_model=ApiResponse)
def transition_load_status(
    load_id: uuid.UUID,
    payload: LoadStatusTransitionRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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

    transitioned_load = service.get_load(str(load_id))
    try:
        notifier = OperationalNotificationService(db)
        old_status = str(result.get("old_status") or "")
        new_status = str(result.get("new_status") or "")
        if (
            parsed_status in {LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING}
            and old_status != new_status
        ):
            notifier.invoice_submitted(load=transitioned_load)
        if parsed_status == LoadStatus.FULLY_PAID and old_status != new_status:
            payment_record = getattr(transitioned_load, "payment_record", None)
            if payment_record is not None:
                notifier.payment_status_updated(record=payment_record, previous_status=old_status)
    except Exception:
        logger.exception("Load status notification failed", extra={"load_id": str(load_id)})

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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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


@router.get("/loads/{load_id}/packet-audit", response_model=ApiResponse)
def get_load_packet_audit(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_read(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    audit = PacketAuditService(db).audit_load(
        load_id=str(load_id), org_id=str(load.organization_id)
    )
    return ApiResponse(data=audit.to_dict(), meta={}, error=None)


@router.get("/loads/{load_id}/submission-packets", response_model=ApiResponse)
def list_submission_packets(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_read(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    packet_service = SubmissionPacketService(db)
    audit_service = PacketAuditService(db)
    packets = packet_service.list_packets(load_id=str(load_id), org_id=str(load.organization_id))
    for packet in packets:
        packet.packet_audit = audit_service.audit_load(
            load_id=str(load_id), org_id=str(load.organization_id), packet_id=str(packet.id)
        )
    return ApiResponse(
        data=[_serialize_submission_packet(packet) for packet in packets], meta={}, error=None
    )


@router.post("/loads/{load_id}/submission-packets", response_model=ApiResponse)
def create_submission_packet(
    load_id: uuid.UUID,
    payload: SubmissionPacketCreateRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_write(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    packet_service = SubmissionPacketService(db)
    packet = packet_service.create_packet_from_load(
        load_id=str(load_id),
        org_id=str(load.organization_id),
        actor=str(token_payload.get("staff_user_id"))
        if token_payload.get("staff_user_id")
        else None,
    )
    if payload.notes:
        packet.notes = payload.notes.strip()

    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="submission_packet",
        entity_id=packet.id,
        action="packet.created",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number},
    )
    db.commit()
    return ApiResponse(data=_serialize_submission_packet(packet), meta={}, error=None)


@router.get("/loads/{load_id}/submission-packets/{packet_id}", response_model=ApiResponse)
def get_submission_packet(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_read(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    packet_service = SubmissionPacketService(db)
    packet = packet_service.get_packet(str(packet_id), str(load_id), str(load.organization_id))
    packet.packet_audit = PacketAuditService(db).audit_load(
        load_id=str(load_id), org_id=str(load.organization_id), packet_id=str(packet_id)
    )
    return ApiResponse(data=_serialize_submission_packet(packet), meta={}, error=None)


@router.get("/loads/{load_id}/submission-packets/{packet_id}/download")
def download_submission_packet_zip(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> StreamingResponse:
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_submission_download(item=load, token_payload=token_payload)

    zip_bytes, load_number = SubmissionPacketService(db).build_packet_zip(
        packet_id=str(packet_id),
        load_id=str(load_id),
        org_id=str(load.organization_id),
    )
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="packet-{load_number}.zip"'},
    )


@router.post(
    "/loads/{load_id}/submission-packets/{packet_id}/mark-sent", response_model=ApiResponse
)
def mark_submission_packet_sent(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    payload: SubmissionPacketMarkSentRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_write(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    packet_service = SubmissionPacketService(db)
    packet = packet_service.mark_sent(
        str(packet_id),
        str(load_id),
        str(load.organization_id),
        {
            "destination_type": payload.destination_type,
            "destination_name": payload.destination_name,
            "destination_email": payload.destination_email,
        },
        str(token_payload.get("staff_user_id")) if token_payload.get("staff_user_id") else None,
    )
    if payload.notes:
        packet.notes = payload.notes.strip()
    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="submission_packet",
        entity_id=packet.id,
        action="packet.sent",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number, "status": "sent"},
    )
    db.commit()
    return ApiResponse(data=_serialize_submission_packet(packet), meta={}, error=None)


@router.get(
    "/loads/{load_id}/submission-packets/{packet_id}/email-history", response_model=ApiResponse
)
def get_submission_packet_email_history(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_read(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)
    packet = SubmissionPacketService(db).get_packet(
        str(packet_id), str(load_id), str(load.organization_id)
    )
    return ApiResponse(data=_serialize_packet_email_history(packet), meta={}, error=None)


@router.post(
    "/loads/{load_id}/submission-packets/{packet_id}/send-email", response_model=ApiResponse
)
def send_submission_packet_email(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    payload: SubmissionPacketSendEmailRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_write(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)

    packet_service = SubmissionPacketService(db)
    packet = packet_service.get_packet(str(packet_id), str(load_id), str(load.organization_id))
    actor_id = (
        str(token_payload.get("staff_user_id")) if token_payload.get("staff_user_id") else None
    )
    normalized_to_email = _normalize_packet_recipient_email(payload.to_email)
    default_subject, default_body = _build_default_packet_email(packet=packet, load=load)
    normalized_subject = _normalize_optional_text(payload.subject) or default_subject
    normalized_body = _normalize_optional_text(payload.body) or default_body

    packet_service._add_event(  # noqa: SLF001
        str(load.organization_id),
        str(load.id),
        str(packet.id),
        "packet_email_send_attempt",
        f"Attempting packet email send to {normalized_to_email}.",
        actor_id,
    )
    db.flush()

    email_service = PacketEmailService()
    try:
        attachments, _load_number = packet_service.build_packet_email_attachments(
            packet_id=str(packet.id),
            load_id=str(load.id),
            org_id=str(load.organization_id),
        )
    except ValidationError as exc:
        packet_service._add_event(  # noqa: SLF001
            str(load.organization_id),
            str(load.id),
            str(packet.id),
            "packet_email_failed",
            (
                f"Packet email failed for {normalized_to_email}; "
                f"subject={normalized_subject}; attachments=0."
            ),
            actor_id,
        )
        db.commit()
        raise exc
    packet_audit = PacketAuditService(db).audit_load(
        load_id=str(load_id), org_id=str(load.organization_id), packet_id=str(packet_id)
    )
    if packet_audit.has_blocking_findings:
        packet_service._add_event(  # noqa: SLF001
            str(load.organization_id),
            str(load.id),
            str(packet.id),
            "packet_email_failed",
            (
                f"Packet email blocked by audit for {normalized_to_email}; "
                f"subject={normalized_subject}; attachments={len(attachments)}."
            ),
            actor_id,
        )
        db.commit()
        raise ValidationError(
            (
                "Billing packet audit found blocking issues. "
                "Fix the audit findings before emailing the packet."
            ),
            details={"packet_audit": packet_audit.to_dict()},
        )

    attachment_count = len(attachments)
    send_result = email_service.send_email_with_attachments(
        to=normalized_to_email,
        subject=normalized_subject,
        body=normalized_body,
        attachments=[
            {
                "filename": str(attachment["filename"]),
                "content_type": str(attachment["content_type"]),
                "bytes": attachment["bytes"],
            }
            for attachment in attachments
        ],
        cc=payload.cc,
        bcc=payload.bcc,
    )

    sanitized_result = _sanitize_packet_send_result(send_result)

    if not bool(send_result.get("accepted")):
        error_message = str(send_result.get("error_message") or "Failed to send packet email.")
        logger.warning(
            (
                "Billing packet email failed: organization_id=%s load_id=%s "
                "recipient=%s attachment_count=%s"
            ),
            load.organization_id,
            load.id,
            normalized_to_email,
            attachment_count,
        )
        packet_service._add_event(  # noqa: SLF001
            str(load.organization_id),
            str(load.id),
            str(packet.id),
            "packet_email_failed",
            (
                f"Packet email {sanitized_result['status']} for {normalized_to_email}; "
                f"subject={normalized_subject}; attachments={attachment_count}."
            ),
            actor_id,
        )
        db.commit()
        if "disabled" in error_message.lower():
            raise ConflictError(
                "Email sending is disabled or not configured. "
                "Download the packet ZIP or try again after email is configured."
            )
        raise ValidationError(
            "Packet email could not be sent. Check email configuration and try again."
        )

    provider = str(send_result.get("provider") or "smtp")
    provider_message_id = _normalize_optional_text(
        str(send_result.get("provider_message_id") or "")
    )
    success_message = (
        f"Packet email sent to {normalized_to_email} via {provider}; "
        f"subject={normalized_subject}; attachments={attachment_count}."
    )
    if provider_message_id:
        success_message = f"{success_message} Provider message id: {provider_message_id}."
    packet_service._add_event(  # noqa: SLF001
        str(load.organization_id),
        str(load.id),
        str(packet.id),
        "packet_email_sent",
        success_message,
        actor_id,
    )

    if not getattr(packet, "sent_at", None):
        packet.sent_at = datetime.now(timezone.utc)
    if not getattr(packet, "sent_by_staff_user_id", None):
        packet.sent_by_staff_user_id = uuid.UUID(actor_id) if actor_id else None
    packet.destination_email = normalized_to_email
    packet.destination_type = packet.destination_type or "broker"
    packet.destination_name = packet.destination_name or (
        getattr(load, "broker_name_raw", None) or "Broker/AP"
    )
    if (packet.status or "").lower() != "sent":
        packet.status = "sent"

    packet_follow_ups = list(
        db.scalars(
            select(FollowUpTask).where(
                FollowUpTask.organization_id == load.organization_id,
                FollowUpTask.load_id == load.id,
                FollowUpTask.submission_packet_id == packet.id,
                FollowUpTask.task_type == FollowUpTaskType.PACKET_FOLLOW_UP,
                FollowUpTask.status.in_([FollowUpTaskStatus.OPEN, FollowUpTaskStatus.SNOOZED]),
            )
        ).all()
    )
    for task in packet_follow_ups:
        task.status = FollowUpTaskStatus.CANCELED

    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="submission_packet",
        entity_id=packet.id,
        action="packet.email_sent",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number, "status": "sent"},
    )
    db.commit()
    refreshed_packet = packet_service.get_packet(
        str(packet_id), str(load_id), str(load.organization_id)
    )
    return ApiResponse(
        data=_serialize_submission_packet(refreshed_packet),
        meta={"email_send_result": sanitized_result},
        error=None,
    )


@router.post(
    "/loads/{load_id}/submission-packets/{packet_id}/mark-accepted", response_model=ApiResponse
)
def mark_submission_packet_accepted(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_write(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)
    packet = SubmissionPacketService(db).mark_accepted(
        str(packet_id),
        str(load_id),
        str(load.organization_id),
        str(token_payload.get("staff_user_id")) if token_payload.get("staff_user_id") else None,
    )
    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="submission_packet",
        entity_id=packet.id,
        action="packet.accepted",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number, "status": "accepted"},
    )
    db.commit()
    return ApiResponse(data=_serialize_submission_packet(packet), meta={}, error=None)


@router.post(
    "/loads/{load_id}/submission-packets/{packet_id}/mark-rejected", response_model=ApiResponse
)
def mark_submission_packet_rejected(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    payload: SubmissionPacketMarkRejectedRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _authorize_submission_write(token_payload)
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)
    packet = SubmissionPacketService(db).mark_rejected(
        str(packet_id),
        str(load_id),
        str(load.organization_id),
        payload.reason,
        str(token_payload.get("staff_user_id")) if token_payload.get("staff_user_id") else None,
        resubmission_required=payload.resubmission_required,
    )
    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="submission_packet",
        entity_id=packet.id,
        action="packet.rejected",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number, "status": "rejected"},
    )
    db.commit()
    return ApiResponse(data=_serialize_submission_packet(packet), meta={}, error=None)


@router.get("/loads/{load_id}/invoice")
def download_load_invoice(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> StreamingResponse:
    service = LoadService(db)
    load = service.get_load(str(load_id))
    _authorize_load_access(item=load, token_payload=token_payload)
    try:
        pdf_bytes = _generate_and_persist_invoice_pdf(db=db, load=load)
    except ValidationError as exc:
        details = exc.details if isinstance(exc.details, dict) else {}
        if details.get("code") == "carrier_profile_incomplete":
            raise ValidationError(
                "Complete Carrier Profile before generating invoice.",
                details={
                    "code": "carrier_profile_incomplete",
                    "message": "Complete Carrier Profile before generating invoice.",
                    "missing_fields": details.get("missing_fields", []),
                    "action_url": details.get("action_url", "/dashboard/settings/carrier-profile"),
                },
                status_code=422,
            ) from exc
        raise
    _log_load_activity(
        db=db,
        organization_id=load.organization_id,
        entity_type="invoice",
        entity_id=load.id,
        action="invoice.generated",
        token_payload=token_payload,
        metadata={"load_id": str(load.id), "load_number": load.load_number},
    )
    db.commit()
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
    writer.writerow(
        [
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
        ]
    )

    for item in items:
        row = _serialize_load(item, detailed=False, db=db)
        writer.writerow(
            [
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
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="loads-export.csv"'},
    )
