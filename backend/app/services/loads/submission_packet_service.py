from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums.document_type import DocumentType
from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.submission_event import SubmissionEvent
from app.domain.models.submission_packet import SubmissionPacket
from app.domain.models.submission_packet_document import SubmissionPacketDocument
from app.services.loads.load_service import LoadService

REQUIRED_DOC_TYPES = {
    DocumentType.INVOICE.value,
    DocumentType.RATE_CONFIRMATION.value,
    DocumentType.PROOF_OF_DELIVERY.value,
}


class SubmissionPacketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_service = LoadService(db)

    def create_packet_from_load(self, load_id: str, org_id: str, actor: str | None = None) -> SubmissionPacket:
        load = self._get_load(load_id=load_id, org_id=org_id)
        documents = self._get_load_documents(load_id=str(load.id), org_id=org_id)
        type_to_doc = self._latest_documents_by_type(documents)
        missing = sorted(doc_type for doc_type in REQUIRED_DOC_TYPES if doc_type not in type_to_doc)
        if missing:
            raise ValidationError(
                "Missing required submission documents",
                details={"missing_documents": missing},
            )

        packet = SubmissionPacket(
            organization_id=load.organization_id,
            load_id=load.id,
            packet_reference=self._next_packet_reference(load_id=str(load.id)),
            destination_type="other",
            status="ready",
            created_by_staff_user_id=self._optional_uuid(actor),
        )
        self.db.add(packet)
        self.db.flush()

        for document in documents:
            if document.id is None:
                continue
            self.db.add(
                SubmissionPacketDocument(
                    submission_packet_id=packet.id,
                    document_id=document.id,
                    document_type=self._doc_type_value(document),
                    filename_snapshot=document.original_filename,
                )
            )

        self._add_event(
            organization_id=org_id,
            load_id=str(load.id),
            packet_id=str(packet.id),
            event_type="packet_created",
            message=f"Billing packet {packet.packet_reference} created.",
            actor=actor,
        )
        self.db.flush()
        self.db.expire_all()
        return self.get_packet(str(packet.id), load_id=str(load.id), org_id=org_id)

    def list_packets(self, load_id: str, org_id: str) -> list[SubmissionPacket]:
        self._get_load(load_id=load_id, org_id=org_id)
        stmt = (
            select(SubmissionPacket)
            .options(selectinload(SubmissionPacket.documents), selectinload(SubmissionPacket.events))
            .where(SubmissionPacket.organization_id == uuid.UUID(org_id), SubmissionPacket.load_id == uuid.UUID(load_id))
            .order_by(SubmissionPacket.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_packet(self, packet_id: str, load_id: str, org_id: str) -> SubmissionPacket:
        stmt = (
            select(SubmissionPacket)
            .options(
                selectinload(SubmissionPacket.documents).selectinload(SubmissionPacketDocument.document),
                selectinload(SubmissionPacket.events),
            )
            .where(
                SubmissionPacket.id == uuid.UUID(packet_id),
                SubmissionPacket.load_id == uuid.UUID(load_id),
                SubmissionPacket.organization_id == uuid.UUID(org_id),
            )
        )
        packet = self.db.scalar(stmt)
        if packet is None:
            raise NotFoundError("Submission packet not found", details={"packet_id": packet_id})
        return packet

    def mark_sent(self, packet_id: str, load_id: str, org_id: str, destination: dict[str, str | None], actor: str | None) -> SubmissionPacket:
        packet = self.get_packet(packet_id, load_id, org_id)
        packet.destination_type = (destination.get("destination_type") or "other").strip().lower()
        packet.destination_name = self._clean(destination.get("destination_name"))
        packet.destination_email = self._clean(destination.get("destination_email"))
        packet.sent_at = datetime.now(timezone.utc)
        packet.sent_by_staff_user_id = self._optional_uuid(actor)
        packet.status = "sent"

        if packet.destination_type == "factoring":
            self.load_service.update_load(load_id=str(packet.load_id), status=LoadStatus.SUBMITTED_TO_FACTORING)
        elif packet.destination_type in {"broker", "customer_ap"}:
            self.load_service.update_load(load_id=str(packet.load_id), status=LoadStatus.SUBMITTED_TO_BROKER)

        self._add_event(
            organization_id=org_id,
            load_id=load_id,
            packet_id=packet_id,
            event_type="packet_sent",
            message=f"Packet marked sent to {packet.destination_type}.",
            actor=actor,
        )
        self.db.flush()
        self.db.expire_all()
        return self.get_packet(packet_id, load_id, org_id)

    def mark_accepted(self, packet_id: str, load_id: str, org_id: str, actor: str | None) -> SubmissionPacket:
        packet = self.get_packet(packet_id, load_id, org_id)
        packet.status = "accepted"
        packet.accepted_at = datetime.now(timezone.utc)
        self._add_event(org_id, load_id, packet_id, "packet_accepted", "Packet accepted.", actor)
        self.db.flush()
        self.db.expire_all()
        return self.get_packet(packet_id, load_id, org_id)

    def mark_rejected(
        self,
        packet_id: str,
        load_id: str,
        org_id: str,
        reason: str,
        actor: str | None,
        *,
        resubmission_required: bool = False,
    ) -> SubmissionPacket:
        normalized_reason = self._clean(reason)
        if not normalized_reason:
            raise ValidationError("rejection reason is required", details={"reason": reason})
        packet = self.get_packet(packet_id, load_id, org_id)
        packet.status = "resubmission_required" if resubmission_required else "rejected"
        packet.rejected_at = datetime.now(timezone.utc)
        event_type = "resubmission_requested" if resubmission_required else "packet_rejected"
        self._add_event(org_id, load_id, packet_id, event_type, normalized_reason, actor)
        self.db.flush()
        self.db.expire_all()
        return self.get_packet(packet_id, load_id, org_id)

    def _add_event(
        self,
        organization_id: str,
        load_id: str,
        packet_id: str | None,
        event_type: str,
        message: str | None,
        actor: str | None,
    ) -> None:
        self.db.add(
            SubmissionEvent(
                organization_id=uuid.UUID(organization_id),
                load_id=uuid.UUID(load_id),
                submission_packet_id=uuid.UUID(packet_id) if packet_id else None,
                event_type=event_type,
                message=message,
                created_by_staff_user_id=self._optional_uuid(actor),
            )
        )

    def _get_load(self, *, load_id: str, org_id: str) -> Load:
        load = self.load_service.get_load(load_id)
        if str(load.organization_id) != org_id:
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def _get_load_documents(self, *, load_id: str, org_id: str) -> list[LoadDocument]:
        stmt = select(LoadDocument).where(
            LoadDocument.organization_id == uuid.UUID(org_id),
            LoadDocument.load_id == uuid.UUID(load_id),
        )
        return list(self.db.scalars(stmt).all())

    def _next_packet_reference(self, *, load_id: str) -> str:
        existing_count = int(
            self.db.scalar(
                select(func.count()).select_from(SubmissionPacket).where(SubmissionPacket.load_id == uuid.UUID(load_id))
            )
            or 0
        )
        return f"PKT-{load_id[:8].upper()}-{existing_count + 1:03d}"

    def _latest_documents_by_type(self, documents: list[LoadDocument]) -> dict[str, LoadDocument]:
        selected: dict[str, LoadDocument] = {}
        for document in documents:
            key = self._doc_type_value(document)
            if key not in selected:
                selected[key] = document
        return selected

    def _doc_type_value(self, document: LoadDocument) -> str:
        document_type = getattr(document, "document_type", None)
        return getattr(document_type, "value", str(document_type or "unknown"))

    def _optional_uuid(self, value: str | None) -> uuid.UUID | None:
        cleaned = self._clean(value)
        if not cleaned:
            return None
        return uuid.UUID(cleaned)

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
