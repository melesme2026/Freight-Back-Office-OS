from __future__ import annotations

# ruff: noqa: E501
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.exceptions import NotFoundError
from app.domain.enums.document_type import DocumentType
from app.domain.models.extracted_field import ExtractedField
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.submission_event import SubmissionEvent
from app.domain.models.submission_packet import SubmissionPacket
from app.domain.models.submission_packet_document import SubmissionPacketDocument
from app.services.loads.load_service import LoadService
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

AuditStatus = str
AuditSeverity = str


@dataclass(frozen=True)
class PacketAuditFinding:
    code: str
    severity: AuditSeverity
    message: str
    affected_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "affected_documents": self.affected_documents,
        }


@dataclass(frozen=True)
class PacketAuditResult:
    status: AuditStatus
    confidence_score: int
    findings: list[PacketAuditFinding]
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "confidence_score": self.confidence_score,
            "findings": [finding.to_dict() for finding in self.findings],
            "generated_at": self.generated_at.isoformat(),
        }

    @property
    def has_blocking_findings(self) -> bool:
        return any(finding.severity == "blocking" for finding in self.findings)


class PacketAuditService:
    """Deterministic, explainable billing packet audit engine."""

    REQUIRED_DOCUMENT_RULES: tuple[tuple[DocumentType, str, AuditSeverity], ...] = (
        (DocumentType.PROOF_OF_DELIVERY, "missing_pod", "blocking"),
        (DocumentType.BILL_OF_LADING, "missing_bol", "warning"),
        (DocumentType.RATE_CONFIRMATION, "missing_rate_confirmation", "blocking"),
        (DocumentType.INVOICE, "missing_invoice", "blocking"),
    )

    AMOUNT_TOLERANCE = Decimal("0.01")

    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_service = LoadService(db)

    def audit_load(
        self, *, load_id: str, org_id: str, packet_id: str | None = None
    ) -> PacketAuditResult:
        load = self._get_load(load_id=load_id, org_id=org_id)
        documents = self._get_documents(load_id=load_id, org_id=org_id)
        packet = (
            self._get_packet(packet_id=packet_id, load_id=load_id, org_id=org_id)
            if packet_id
            else None
        )
        packet_documents = list(getattr(packet, "documents", None) or []) if packet else []
        findings: list[PacketAuditFinding] = []

        findings.extend(
            self._required_document_findings(documents=documents, packet_documents=packet_documents)
        )
        findings.extend(self._unsigned_pod_findings(documents=documents))
        findings.extend(self._amount_findings(load=load, documents=documents))
        findings.extend(self._duplicate_invoice_findings(load=load, packet=packet))
        findings.extend(self._lumper_findings(load=load, documents=documents))
        findings.extend(self._broker_reference_findings(load=load, documents=documents))

        return PacketAuditResult(
            status=self._status(findings),
            confidence_score=self._confidence_score(
                findings=findings, documents=documents, load=load
            ),
            findings=findings,
            generated_at=datetime.now(timezone.utc),
        )

    def _required_document_findings(
        self,
        *,
        documents: list[LoadDocument],
        packet_documents: list[SubmissionPacketDocument],
    ) -> list[PacketAuditFinding]:
        present_types = {self._doc_type(document.document_type) for document in documents}
        packet_types = {
            self._clean(getattr(item, "document_type", None)) for item in packet_documents
        }
        findings: list[PacketAuditFinding] = []
        for document_type, code, severity in self.REQUIRED_DOCUMENT_RULES:
            doc_type = document_type.value
            if doc_type in present_types and (not packet_documents or doc_type in packet_types):
                continue
            label = self._document_label(doc_type)
            scope = "packet snapshot" if packet_documents and doc_type in present_types else "load"
            findings.append(
                PacketAuditFinding(
                    code=code,
                    severity=severity,
                    message=f"{label} is missing from the billing {scope}; add it before sending the invoice packet.",
                    affected_documents=[doc_type],
                )
            )
        return findings

    def _unsigned_pod_findings(self, *, documents: list[LoadDocument]) -> list[PacketAuditFinding]:
        pod_docs = [
            doc
            for doc in documents
            if self._doc_type(doc.document_type) == DocumentType.PROOF_OF_DELIVERY.value
        ]
        findings: list[PacketAuditFinding] = []
        for document in pod_docs:
            signature_field = self._first_field(
                document, {"signature_present", "pod_signature_present", "signed"}
            )
            if signature_field is None:
                findings.append(
                    PacketAuditFinding(
                        code="possible_unsigned_pod",
                        severity="warning",
                        message="POD signature could not be verified from available OCR metadata; visually confirm the receiver signature before sending.",
                        affected_documents=[str(document.id)],
                    )
                )
                continue
            if self._falsey_text(signature_field):
                findings.append(
                    PacketAuditFinding(
                        code="possible_unsigned_pod",
                        severity="warning",
                        message="POD metadata indicates the delivery signature may be missing; confirm or upload a signed POD.",
                        affected_documents=[str(document.id)],
                    )
                )
        return findings

    def _amount_findings(
        self, *, load: Load, documents: list[LoadDocument]
    ) -> list[PacketAuditFinding]:
        invoice_amount = self._first_amount(
            documents,
            {"invoice_amount", "invoice_total", "total_amount"},
            DocumentType.INVOICE.value,
        )
        load_amount = self._decimal(getattr(load, "gross_amount", None))
        payment_record = self._payment_record(load=load)
        funded_amount = (
            self._first_present_decimal(
                getattr(payment_record, "advance_amount", None),
                getattr(payment_record, "amount_received", None),
                getattr(payment_record, "expected_amount", None),
            )
            if payment_record
            else None
        )

        findings: list[PacketAuditFinding] = []
        if invoice_amount is None or load_amount is None:
            return findings
        if abs(invoice_amount - load_amount) > self.AMOUNT_TOLERANCE:
            findings.append(
                PacketAuditFinding(
                    code="amount_mismatch",
                    severity="warning",
                    message=f"Invoice amount {invoice_amount} does not match load gross amount {load_amount}; verify invoice totals before submission.",
                    affected_documents=[DocumentType.INVOICE.value],
                )
            )
        if (
            funded_amount is not None
            and funded_amount > Decimal("0.00")
            and abs(invoice_amount - funded_amount) > self.AMOUNT_TOLERANCE
        ):
            findings.append(
                PacketAuditFinding(
                    code="funded_amount_mismatch",
                    severity="warning",
                    message=f"Invoice amount {invoice_amount} differs from factoring/payment amount {funded_amount}; reconcile funding context before closing the packet.",
                    affected_documents=[DocumentType.INVOICE.value],
                )
            )
        return findings

    def _duplicate_invoice_findings(
        self, *, load: Load, packet: SubmissionPacket | None
    ) -> list[PacketAuditFinding]:
        invoice_number = self._clean(getattr(load, "invoice_number", None))
        findings: list[PacketAuditFinding] = []
        if invoice_number:
            duplicate_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(Load)
                    .where(
                        Load.organization_id == load.organization_id,
                        Load.invoice_number == invoice_number,
                        Load.id != load.id,
                    )
                )
                or 0
            )
            if duplicate_count > 0:
                findings.append(
                    PacketAuditFinding(
                        code="duplicate_invoice_number",
                        severity="blocking",
                        message=f"Invoice number {invoice_number} is already used on another load in this organization; assign a unique invoice number before sending.",
                        affected_documents=[DocumentType.INVOICE.value],
                    )
                )
        if packet is not None:
            sent_attempt_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(SubmissionEvent)
                    .where(
                        SubmissionEvent.submission_packet_id == packet.id,
                        SubmissionEvent.event_type == "packet_email_sent",
                    )
                )
                or 0
            )
            if sent_attempt_count > 0:
                findings.append(
                    PacketAuditFinding(
                        code="repeated_packet_send",
                        severity="warning",
                        message="This packet has already been emailed from the system; confirm the recipient needs another copy before resending.",
                        affected_documents=[str(packet.id)],
                    )
                )
        return findings

    def _lumper_findings(
        self, *, load: Load, documents: list[LoadDocument]
    ) -> list[PacketAuditFinding]:
        has_lumper_doc = any(
            self._doc_type(doc.document_type) == DocumentType.LUMPER_RECEIPT.value
            for doc in documents
        )
        if has_lumper_doc:
            return []
        text = " ".join(
            value
            for value in [getattr(load, "notes", None), getattr(load, "factoring_notes", None)]
            if value
        ).lower()
        accessorial_amount = self._first_amount(
            documents, {"lumper_amount", "lumper_fee", "accessorial_amount"}
        )
        if "lumper" not in text and accessorial_amount is None:
            return []
        return [
            PacketAuditFinding(
                code="missing_lumper_receipt",
                severity="warning",
                message="Load context mentions lumper/accessorial fees but no lumper receipt is attached; add support or document why it is not needed.",
                affected_documents=[DocumentType.LUMPER_RECEIPT.value],
            )
        ]

    def _broker_reference_findings(
        self, *, load: Load, documents: list[LoadDocument]
    ) -> list[PacketAuditFinding]:
        load_reference = self._clean(
            getattr(load, "rate_confirmation_number", None)
        ) or self._clean(getattr(load, "load_number", None))
        invoice_reference = self._first_text(
            documents,
            {"broker_reference", "broker_ref", "load_reference"},
            DocumentType.INVOICE.value,
        )
        ratecon_reference = self._first_text(
            documents,
            {"broker_reference", "broker_ref", "rate_confirmation_number", "load_reference"},
            DocumentType.RATE_CONFIRMATION.value,
        )
        references = [
            ("load", load_reference),
            ("invoice", invoice_reference),
            ("rate confirmation", ratecon_reference),
        ]
        normalized = [(label, self._reference_key(value)) for label, value in references if value]
        if len({value for _, value in normalized}) <= 1:
            return []
        visible = ", ".join(f"{label}: {value}" for label, value in references if value)
        return [
            PacketAuditFinding(
                code="broker_reference_mismatch",
                severity="warning",
                message=f"Broker/load references do not agree ({visible}); confirm the invoice references the same broker load.",
                affected_documents=[
                    DocumentType.INVOICE.value,
                    DocumentType.RATE_CONFIRMATION.value,
                ],
            )
        ]

    def _confidence_score(
        self, *, findings: list[PacketAuditFinding], documents: list[LoadDocument], load: Load
    ) -> int:
        score = 100
        score -= sum(25 for finding in findings if finding.severity == "blocking")
        score -= sum(10 for finding in findings if finding.severity == "warning")
        score -= sum(3 for finding in findings if finding.severity == "info")
        if not any(getattr(document, "extracted_fields", None) for document in documents):
            score -= 10
        if getattr(load, "extraction_confidence_avg", None) is None:
            score -= 5
        return max(0, min(100, score))

    @staticmethod
    def _status(findings: list[PacketAuditFinding]) -> AuditStatus:
        if any(finding.severity == "blocking" for finding in findings):
            return "failed"
        if any(finding.severity == "warning" for finding in findings):
            return "warning"
        return "passed"

    def _get_load(self, *, load_id: str, org_id: str) -> Load:
        load = self.load_service.get_load(load_id)
        if str(load.organization_id) != org_id:
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def _get_packet(self, *, packet_id: str, load_id: str, org_id: str) -> SubmissionPacket:
        packet = self.db.scalar(
            select(SubmissionPacket)
            .options(
                selectinload(SubmissionPacket.documents), selectinload(SubmissionPacket.events)
            )
            .where(
                SubmissionPacket.id == uuid.UUID(packet_id),
                SubmissionPacket.load_id == uuid.UUID(load_id),
                SubmissionPacket.organization_id == uuid.UUID(org_id),
            )
        )
        if packet is None:
            raise NotFoundError("Submission packet not found", details={"packet_id": packet_id})
        return packet

    def _get_documents(self, *, load_id: str, org_id: str) -> list[LoadDocument]:
        return list(
            self.db.scalars(
                select(LoadDocument)
                .options(selectinload(LoadDocument.extracted_fields))
                .where(
                    LoadDocument.organization_id == uuid.UUID(org_id),
                    LoadDocument.load_id == uuid.UUID(load_id),
                )
            ).all()
        )

    def _payment_record(self, *, load: Load) -> LoadPaymentRecord | None:
        return self.db.scalar(select(LoadPaymentRecord).where(LoadPaymentRecord.load_id == load.id))

    @classmethod
    def _first_amount(
        cls, documents: list[LoadDocument], field_names: set[str], document_type: str | None = None
    ) -> Decimal | None:
        field = cls._first_field_from_documents(documents, field_names, document_type)
        if field is None:
            return None
        return cls._decimal(getattr(field, "field_value_number", None)) or cls._decimal(
            getattr(field, "field_value_text", None)
        )

    @classmethod
    def _first_text(
        cls, documents: list[LoadDocument], field_names: set[str], document_type: str | None = None
    ) -> str | None:
        field = cls._first_field_from_documents(documents, field_names, document_type)
        if field is None:
            return None
        return cls._clean(getattr(field, "field_value_text", None))

    @classmethod
    def _first_field_from_documents(
        cls, documents: list[LoadDocument], field_names: set[str], document_type: str | None
    ) -> ExtractedField | None:
        normalized_names = {name.strip().lower() for name in field_names}
        for document in documents:
            if document_type and cls._doc_type(document.document_type) != document_type:
                continue
            field = cls._first_field(document, normalized_names)
            if field is not None:
                return field
        return None

    @classmethod
    def _first_field(cls, document: LoadDocument, field_names: set[str]) -> ExtractedField | None:
        for extracted_field in getattr(document, "extracted_fields", None) or []:
            if cls._clean(getattr(extracted_field, "field_name", None), lower=True) in field_names:
                return extracted_field
        return None

    @staticmethod
    def _falsey_text(field: ExtractedField) -> bool:
        value = getattr(field, "field_value_text", None)
        if value is None and getattr(field, "field_value_number", None) is not None:
            value = str(field.field_value_number)
        normalized = str(value or "").strip().lower()
        return normalized in {"false", "no", "0", "missing", "unsigned", "not signed"}

    @classmethod
    def _first_present_decimal(cls, *values: Any) -> Decimal | None:
        for value in values:
            decimal_value = cls._decimal(value)
            if decimal_value is not None:
                return decimal_value
        return None

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            cleaned = str(value).replace("$", "").replace(",", "").strip()
            return Decimal(cleaned).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _document_label(document_type: str) -> str:
        return document_type.replace("_", " ").title().replace("Pod", "POD").replace("Bol", "BOL")

    @staticmethod
    def _reference_key(value: str | None) -> str | None:
        if not value:
            return None
        return "".join(char for char in value.lower() if char.isalnum()) or None

    @staticmethod
    def _doc_type(value: Any) -> str:
        return getattr(value, "value", str(value or "unknown"))

    @staticmethod
    def _clean(value: Any, *, lower: bool = False) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if lower:
            normalized = normalized.lower()
        return normalized or None
