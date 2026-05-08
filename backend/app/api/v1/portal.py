from __future__ import annotations

import io
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.documents import (
    MAX_UPLOAD_FILE_SIZE_BYTES,
    _normalize_optional_text,
    _to_iso_or_none,
    _validate_upload_file,
)
from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError, ValidationError
from app.core.security import create_action_token, decode_token, get_bearer_token, get_current_token_payload
from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.models.load_document import LoadDocument
from app.repositories.load_repo import LoadRepository
from app.schemas.common import ApiResponse
from app.services.audit.audit_service import AuditService
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.packet_readiness import calculate_packet_readiness
from app.services.loads.submission_packet_service import SubmissionPacketService
from sqlalchemy import desc, select

router = APIRouter()

PORTAL_TOKEN_TYPE = "external_portal"
PORTAL_ROLES = {"broker", "customer", "ap_ar", "logistics_stakeholder"}
PORTAL_DOWNLOAD_DOCUMENT_TYPES = {
    DocumentType.INVOICE.value,
    DocumentType.RATE_CONFIRMATION.value,
    DocumentType.PROOF_OF_DELIVERY.value,
    DocumentType.BILL_OF_LADING.value,
}
PORTAL_UPLOAD_DOCUMENT_TYPES = {
    DocumentType.RATE_CONFIRMATION.value,
    DocumentType.BILL_OF_LADING.value,
    DocumentType.PROOF_OF_DELIVERY.value,
    DocumentType.LUMPER_RECEIPT.value,
    DocumentType.DETENTION_SUPPORT.value,
    DocumentType.ACCESSORIAL_SUPPORT.value,
    DocumentType.SCALE_TICKET.value,
    DocumentType.OTHER.value,
}
DEFAULT_PORTAL_EXPIRY_HOURS = 72
MAX_PORTAL_EXPIRY_HOURS = 24 * 14


class PortalAccessLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    load_id: uuid.UUID
    contact_email: str
    contact_name: str | None = None
    role: str = "broker"
    expires_in_hours: int = Field(default=DEFAULT_PORTAL_EXPIRY_HOURS, ge=1, le=MAX_PORTAL_EXPIRY_HOURS)
    allow_packet_download: bool = True
    allow_document_upload: bool = True


def _normalize_role(role: str) -> str:
    normalized = (role or "").strip().lower()
    if normalized not in PORTAL_ROLES:
        raise ValidationError("Invalid portal role", details={"role": role, "allowed_roles": sorted(PORTAL_ROLES)})
    return normalized


def _normalize_email(value: str) -> str:
    normalized = (value or "").strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValidationError("A valid contact_email is required", details={"contact_email": value})
    return normalized


def _portal_payload(token: str = Depends(get_bearer_token)) -> dict[str, Any]:
    payload = decode_token(token, expected_token_type=PORTAL_TOKEN_TYPE)
    role = str(payload.get("role") or "").strip().lower()
    if not role.startswith("external_"):
        raise UnauthorizedError("Invalid portal role")
    required = ["organization_id", "load_id", "customer_account_id", "contact_email"]
    missing = [claim for claim in required if not str(payload.get(claim) or "").strip()]
    if missing:
        raise UnauthorizedError("Portal token is missing required scope")
    return payload


def _staff_actor_id(token_payload: dict[str, Any]) -> str | None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role == "driver" or role.startswith("external_"):
        raise ForbiddenError("External portal access cannot create portal invitations")
    actor = str(token_payload.get("staff_user_id") or token_payload.get("sub") or "").strip()
    return actor or None


def _get_scoped_load(*, db: Session, token_payload: dict[str, Any]):
    load = LoadRepository(db).get_by_id(str(token_payload["load_id"]), include_related=True)
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
    if str(load.organization_id) != str(token_payload["organization_id"]):
        raise UnauthorizedError("Load is not in portal organization scope")
    if str(load.customer_account_id) != str(token_payload["customer_account_id"]):
        raise UnauthorizedError("Load is not in portal customer scope")
    broker_id = token_payload.get("broker_id")
    if broker_id and str(getattr(load, "broker_id", "")) != str(broker_id):
        raise UnauthorizedError("Load is not in portal broker scope")
    return load


def _assert_load_id_scope(load_id: uuid.UUID, token_payload: dict[str, Any]) -> None:
    if str(load_id) != str(token_payload.get("load_id")):
        raise UnauthorizedError("Portal access is scoped to a different load")


def _doc_type_value(value: object | None) -> str | None:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value) if value is not None else None


def _serialize_portal_load(load: Any) -> dict[str, Any]:
    documents = list(getattr(load, "documents", None) or [])
    doc_types = [_doc_type_value(getattr(document, "document_type", None)) for document in documents]
    return {
        "id": str(load.id),
        "load_number": load.load_number,
        "status": _doc_type_value(getattr(load, "status", None)),
        "processing_status": _doc_type_value(getattr(load, "processing_status", None)),
        "pickup_date": _to_iso_or_none(load.pickup_date),
        "delivery_date": _to_iso_or_none(load.delivery_date),
        "pickup_location": load.pickup_location,
        "delivery_location": load.delivery_location,
        "broker_name": getattr(getattr(load, "broker", None), "name", None) or load.broker_name_raw,
        "customer_account_name": getattr(getattr(load, "customer_account", None), "account_name", None),
        "rate_confirmation_number": load.rate_confirmation_number,
        "bol_number": load.bol_number,
        "invoice_number": load.invoice_number,
        "documents_complete": bool(load.documents_complete),
        "has_ratecon": bool(load.has_ratecon),
        "has_bol": bool(load.has_bol),
        "has_invoice": bool(load.has_invoice),
        "packet_readiness": calculate_packet_readiness(document_types=[doc for doc in doc_types if doc]),
        "submitted_at": _to_iso_or_none(load.submitted_at),
        "paid_at": _to_iso_or_none(load.paid_at),
        "updated_at": _to_iso_or_none(load.updated_at),
    }


def _serialize_portal_document(document: LoadDocument) -> dict[str, Any]:
    document_type = _doc_type_value(getattr(document, "document_type", None))
    return {
        "id": str(document.id),
        "load_id": str(document.load_id) if document.load_id else None,
        "document_type": document_type,
        "original_filename": document.original_filename,
        "mime_type": document.mime_type,
        "file_size_bytes": document.file_size_bytes,
        "processing_status": _doc_type_value(getattr(document, "processing_status", None)),
        "received_at": _to_iso_or_none(document.received_at),
        "created_at": _to_iso_or_none(document.created_at),
        "download_allowed": document_type in PORTAL_DOWNLOAD_DOCUMENT_TYPES,
    }


def _latest_documents_for_load(*, db: Session, organization_id: str, load_id: str) -> list[LoadDocument]:
    stmt = (
        select(LoadDocument)
        .where(LoadDocument.organization_id == uuid.UUID(organization_id), LoadDocument.load_id == uuid.UUID(load_id))
        .order_by(desc(LoadDocument.received_at), desc(LoadDocument.created_at))
    )
    return list(db.scalars(stmt).all())


def _serialize_portal_packet(packet: Any) -> dict[str, Any]:
    return {
        "id": str(packet.id),
        "packet_reference": packet.packet_reference,
        "status": packet.status,
        "destination_type": packet.destination_type,
        "sent_at": _to_iso_or_none(packet.sent_at),
        "accepted_at": _to_iso_or_none(packet.accepted_at),
        "rejected_at": _to_iso_or_none(packet.rejected_at),
        "created_at": _to_iso_or_none(packet.created_at),
        "documents": [
            {
                "document_id": str(getattr(doc, "document_id", "")),
                "document_type": getattr(doc, "document_type", None),
                "filename_snapshot": getattr(doc, "filename_snapshot", None),
                "created_at": _to_iso_or_none(getattr(doc, "created_at", None)),
            }
            for doc in (getattr(packet, "documents", None) or [])
        ],
    }


def _log_portal_event(*, db: Session, organization_id: str, load_id: str, action: str, token_payload: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
    AuditService(db).log_event(
        organization_id=organization_id,
        entity_type="load",
        entity_id=load_id,
        action=action,
        actor_id=None,
        actor_type="external_portal",
        metadata_json={
            "contact_email": token_payload.get("contact_email"),
            "contact_name": token_payload.get("contact_name"),
            "portal_role": token_payload.get("role"),
            **(metadata or {}),
        },
    )


@router.post("/portal/access-links", response_model=ApiResponse)
def create_portal_access_link(
    payload: PortalAccessLinkRequest,
    *,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    actor_id = _staff_actor_id(token_payload)
    load = LoadRepository(db).get_by_id(payload.load_id, include_related=True)
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
    token_org_id = token_payload.get("organization_id")
    if str(load.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")

    portal_role = _normalize_role(payload.role)
    contact_email = _normalize_email(payload.contact_email)
    expires_in_hours = min(payload.expires_in_hours, MAX_PORTAL_EXPIRY_HOURS)
    claims = {
        "organization_id": str(load.organization_id),
        "customer_account_id": str(load.customer_account_id),
        "broker_id": str(load.broker_id) if load.broker_id else None,
        "load_id": str(load.id),
        "role": f"external_{portal_role}",
        "contact_email": contact_email,
        "contact_name": _normalize_optional_text(payload.contact_name),
        "allow_packet_download": bool(payload.allow_packet_download),
        "allow_document_upload": bool(payload.allow_document_upload),
    }
    portal_token = create_action_token(
        subject=f"portal:{load.id}:{contact_email}",
        token_type=PORTAL_TOKEN_TYPE,
        additional_claims=claims,
        expires_delta=timedelta(hours=expires_in_hours),
    )
    _log_portal_event(
        db=db,
        organization_id=str(load.organization_id),
        load_id=str(load.id),
        action="portal.access_link.created",
        token_payload={"contact_email": contact_email, "contact_name": payload.contact_name, "role": f"external_{portal_role}"},
        metadata={"created_by_staff_user_id": actor_id, "expires_in_hours": expires_in_hours},
    )
    db.commit()
    return ApiResponse(
        data={"access_token": portal_token, "token_type": "Bearer", "expires_in_hours": expires_in_hours, "load_id": str(load.id), "role": f"external_{portal_role}"},
        meta={},
        error=None,
    )


@router.get("/portal/me", response_model=ApiResponse)
def get_portal_scope(
    token_payload: dict[str, Any] = Depends(_portal_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    load = _get_scoped_load(db=db, token_payload=token_payload)
    return ApiResponse(data={"scope": {k: token_payload.get(k) for k in ("organization_id", "customer_account_id", "broker_id", "load_id", "role", "contact_email", "contact_name", "allow_packet_download", "allow_document_upload")}, "load": _serialize_portal_load(load)}, meta={}, error=None)


@router.get("/portal/loads/{load_id}", response_model=ApiResponse)
def get_portal_load(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(_portal_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_load_id_scope(load_id, token_payload)
    load = _get_scoped_load(db=db, token_payload=token_payload)
    docs = _latest_documents_for_load(db=db, organization_id=str(load.organization_id), load_id=str(load.id))
    packets = SubmissionPacketService(db).list_packets(load_id=str(load.id), org_id=str(load.organization_id))
    _log_portal_event(db=db, organization_id=str(load.organization_id), load_id=str(load.id), action="portal.load.viewed", token_payload=token_payload)
    db.commit()
    return ApiResponse(data={"load": _serialize_portal_load(load), "documents": [_serialize_portal_document(doc) for doc in docs], "packets": [_serialize_portal_packet(packet) for packet in packets]}, meta={}, error=None)


@router.get("/portal/loads/{load_id}/packets/{packet_id}/download")
def download_portal_packet(
    load_id: uuid.UUID,
    packet_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(_portal_payload),
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    _assert_load_id_scope(load_id, token_payload)
    if not bool(token_payload.get("allow_packet_download", True)):
        raise ForbiddenError("Packet download is not allowed for this portal link")
    load = _get_scoped_load(db=db, token_payload=token_payload)
    zip_bytes, load_number = SubmissionPacketService(db).build_packet_zip(packet_id=str(packet_id), load_id=str(load.id), org_id=str(load.organization_id))
    _log_portal_event(db=db, organization_id=str(load.organization_id), load_id=str(load.id), action="portal.packet.downloaded", token_payload=token_payload, metadata={"packet_id": str(packet_id)})
    db.commit()
    return StreamingResponse(io.BytesIO(zip_bytes), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="portal-packet-{load_number}.zip"'})


@router.get("/portal/loads/{load_id}/documents/{document_id}/download")
def download_portal_document(
    load_id: uuid.UUID,
    document_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(_portal_payload),
    db: Session = Depends(get_db_session),
):
    _assert_load_id_scope(load_id, token_payload)
    load = _get_scoped_load(db=db, token_payload=token_payload)
    document = DocumentService(db).get_document(str(document_id))
    if str(document.organization_id) != str(load.organization_id) or str(document.load_id) != str(load.id):
        raise UnauthorizedError("Document is not in portal load scope")
    if _doc_type_value(document.document_type) not in PORTAL_DOWNLOAD_DOCUMENT_TYPES:
        raise ForbiddenError("This document is not available in the portal")
    _log_portal_event(db=db, organization_id=str(load.organization_id), load_id=str(load.id), action="portal.document.downloaded", token_payload=token_payload, metadata={"document_id": str(document.id), "document_type": _doc_type_value(document.document_type)})
    db.commit()
    return StorageService().get_file(document.storage_key, download_filename=document.original_filename, media_type=document.mime_type)


@router.post("/portal/loads/{load_id}/documents/upload", response_model=ApiResponse)
async def upload_portal_document(
    load_id: uuid.UUID,
    *,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    token_payload: dict[str, Any] = Depends(_portal_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_load_id_scope(load_id, token_payload)
    if not bool(token_payload.get("allow_document_upload", True)):
        raise ForbiddenError("Document upload is not allowed for this portal link")
    _validate_upload_file(file)
    load = _get_scoped_load(db=db, token_payload=token_payload)
    service = DocumentService(db)
    parsed_type = service._normalize_document_type(document_type)
    parsed_type_value = parsed_type.value
    if parsed_type_value not in PORTAL_UPLOAD_DOCUMENT_TYPES:
        raise ForbiddenError("This document type cannot be uploaded from the external portal")

    storage = StorageService()
    uploaded_storage_key: str | None = None
    try:
        storage_result = await storage.save_file(file, max_size_bytes=MAX_UPLOAD_FILE_SIZE_BYTES)
        uploaded_storage_key = str(storage_result["storage_key"])
        item = service.create_document(
            organization_id=str(load.organization_id),
            customer_account_id=str(load.customer_account_id),
            driver_id=str(load.driver_id) if load.driver_id else None,
            load_id=str(load.id),
            storage_key=uploaded_storage_key,
            storage_bucket=None,
            source_channel=Channel.EXTERNAL_PORTAL,
            document_type=parsed_type,
            original_filename=_normalize_optional_text(file.filename),
            mime_type=_normalize_optional_text(file.content_type),
            file_size_bytes=int(storage_result.get("size") or 0),
        )
        _log_portal_event(db=db, organization_id=str(load.organization_id), load_id=str(load.id), action="portal.document.uploaded", token_payload=token_payload, metadata={"document_id": str(item.id), "document_type": parsed_type_value, "filename": file.filename, "file_size_bytes": storage_result.get("size")})
        db.commit()
        return ApiResponse(data=_serialize_portal_document(item), meta={"uploaded": True, "attribution": {"actor_type": "external_portal", "contact_email": token_payload.get("contact_email")}}, error=None)
    except Exception:
        db.rollback()
        if uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        raise
