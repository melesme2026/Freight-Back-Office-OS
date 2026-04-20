from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateRecordError, NotFoundError, ValidationError
from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load_document import LoadDocument
from app.repositories.document_repo import DocumentRepository
from app.repositories.load_repo import LoadRepository
from app.services.loads.packet_readiness import calculate_packet_readiness


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.load_repo = LoadRepository(db)

    # ---------------------------
    # CORE CREATE
    # ---------------------------

    def create_document(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        storage_key: str,
        source_channel: str | Channel,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_type: str | DocumentType | None = None,
        original_filename: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        storage_bucket: str | None = None,
        page_count: int | None = None,
        uploaded_by_staff_user_id: str | None = None,
        file_bytes: bytes | None = None,
    ) -> LoadDocument:
        normalized_organization_id = self._normalize_required_text(
            "organization_id",
            organization_id,
        )
        normalized_customer_account_id = self._normalize_required_text(
            "customer_account_id",
            customer_account_id,
        )
        normalized_storage_key = self._normalize_required_text("storage_key", storage_key)
        normalized_source_channel = self._normalize_channel(source_channel)
        normalized_driver_id = self._normalize_optional_text(driver_id)
        normalized_load_id = self._normalize_optional_text(load_id)
        normalized_original_filename = self._normalize_optional_text(original_filename)
        normalized_mime_type = self._normalize_optional_text(mime_type)
        normalized_storage_bucket = self._normalize_optional_text(storage_bucket)
        normalized_uploaded_by_staff_user_id = self._normalize_optional_text(
            uploaded_by_staff_user_id
        )

        normalized_document_type = self._normalize_document_type(document_type)
        validated_file_size_bytes = self._validate_non_negative_int(
            "file_size_bytes",
            file_size_bytes,
        )
        validated_page_count = self._validate_non_negative_int("page_count", page_count)

        file_hash_sha256 = self._build_file_hash(
            storage_key=normalized_storage_key,
            file_bytes=file_bytes,
            original_filename=normalized_original_filename,
            file_size_bytes=validated_file_size_bytes,
        )

        existing = self.document_repo.get_by_file_hash(file_hash_sha256=file_hash_sha256)
        if existing is not None:
            raise DuplicateRecordError(
                "Document with the same file already exists",
                details={
                    "document_id": str(existing.id),
                    "file_hash_sha256": file_hash_sha256,
                },
            )

        model = LoadDocument(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
            driver_id=normalized_driver_id,
            load_id=normalized_load_id,
            source_channel=normalized_source_channel,
            document_type=normalized_document_type,
            original_filename=normalized_original_filename,
            mime_type=normalized_mime_type,
            file_size_bytes=validated_file_size_bytes,
            storage_bucket=normalized_storage_bucket,
            storage_key=normalized_storage_key,
            file_hash_sha256=file_hash_sha256,
            page_count=validated_page_count,
            processing_status=ProcessingStatus.PENDING,
            classification_confidence=None,
            ocr_completed_at=None,
            received_at=datetime.now(timezone.utc),
            uploaded_by_staff_user_id=normalized_uploaded_by_staff_user_id,
        )

        created = self.document_repo.create(model)

        if normalized_load_id:
            self._sync_load_document_flags(normalized_load_id)

        return self.document_repo.get_by_id(created.id, include_related=True) or created

    # ---------------------------
    # READ
    # ---------------------------

    def get_document(self, document_id: str) -> LoadDocument:
        normalized_document_id = self._normalize_required_text("document_id", document_id)
        document = self.document_repo.get_by_id(
            normalized_document_id,
            include_related=True,
        )
        if document is None:
            raise NotFoundError(
                "Document not found",
                details={"document_id": normalized_document_id},
            )
        return document

    def get_document_in_organization(
        self,
        *,
        document_id: str,
        organization_id: str,
    ) -> LoadDocument:
        document = self.get_document(document_id)
        normalized_organization_id = self._normalize_required_text(
            "organization_id",
            organization_id,
        )
        if str(document.organization_id) != normalized_organization_id:
            raise NotFoundError(
                "Document not found",
                details={"document_id": document_id, "organization_id": normalized_organization_id},
            )
        return document

    def list_documents(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_type: str | DocumentType | None = None,
        processing_status: str | ProcessingStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[LoadDocument], int]:
        validated_page = self._validate_positive_int("page", page)
        validated_page_size = self._validate_positive_int("page_size", page_size)

        normalized_document_type = self._normalize_document_type(document_type, allow_none=True)
        normalized_processing_status = self._normalize_processing_status(
            processing_status,
            allow_none=True,
        )

        return self.document_repo.list(
            organization_id=self._normalize_optional_text(organization_id),
            customer_account_id=self._normalize_optional_text(customer_account_id),
            driver_id=self._normalize_optional_text(driver_id),
            load_id=self._normalize_optional_text(load_id),
            document_type=normalized_document_type,
            processing_status=normalized_processing_status,
            page=validated_page,
            page_size=validated_page_size,
            include_related=True,
        )

    # ---------------------------
    # UPDATE / PROCESSING
    # ---------------------------

    def mark_processing(
        self,
        *,
        document_id: str,
        processing_status: str | ProcessingStatus,
        classification_confidence: float | None = None,
        page_count: int | None = None,
    ) -> LoadDocument:
        document = self.get_document(document_id)
        normalized_processing_status = self._normalize_processing_status(processing_status)

        document.processing_status = normalized_processing_status

        if classification_confidence is not None:
            document.classification_confidence = self._validate_classification_confidence(
                classification_confidence
            )

        if page_count is not None:
            document.page_count = self._validate_non_negative_int("page_count", page_count)

        if normalized_processing_status == ProcessingStatus.COMPLETED:
            document.ocr_completed_at = datetime.now(timezone.utc)

        updated = self.document_repo.update(document)

        if updated.load_id:
            self._sync_load_document_flags(str(updated.load_id))

        return self.document_repo.get_by_id(updated.id, include_related=True) or updated

    def update_document_type(
        self,
        *,
        document_id: str,
        document_type: str | DocumentType,
        classification_confidence: float | None = None,
    ) -> LoadDocument:
        document = self.get_document(document_id)
        normalized_document_type = self._normalize_document_type(document_type)

        document.document_type = normalized_document_type

        if classification_confidence is not None:
            document.classification_confidence = self._validate_classification_confidence(
                classification_confidence
            )

        updated = self.document_repo.update(document)

        if updated.load_id:
            self._sync_load_document_flags(str(updated.load_id))

        return self.document_repo.get_by_id(updated.id, include_related=True) or updated

    def attach_to_load(
        self,
        *,
        document_id: str,
        load_id: str,
    ) -> LoadDocument:
        normalized_load_id = self._normalize_required_text("load_id", load_id)
        document = self.get_document(document_id)
        document.load_id = normalized_load_id
        updated = self.document_repo.update(document)
        self._sync_load_document_flags(normalized_load_id)
        return self.document_repo.get_by_id(updated.id, include_related=True) or updated

    # ---------------------------
    # DOWNLOAD HELPER
    # ---------------------------

    def get_document_storage_key(self, document_id: str) -> str:
        document = self.get_document(document_id)
        return self._normalize_required_text("storage_key", document.storage_key)

    # ---------------------------
    # REPROCESS
    # ---------------------------

    def reprocess_document(
        self,
        *,
        document_id: str,
        force_reclassification: bool = False,
        force_reextraction: bool = False,
    ) -> dict[str, Any]:
        document = self.get_document(document_id)

        document.processing_status = ProcessingStatus.PENDING

        if force_reclassification:
            document.document_type = DocumentType.UNKNOWN
            document.classification_confidence = None

        if force_reextraction:
            document.ocr_completed_at = None

        self.document_repo.update(document)

        if document.load_id:
            self._sync_load_document_flags(str(document.load_id))

        return {
            "document_id": str(document.id),
            "queued": True,
            "force_reclassification": force_reclassification,
            "force_reextraction": force_reextraction,
        }

    # ---------------------------
    # INTERNAL HELPERS
    # ---------------------------

    def _sync_load_document_flags(self, load_id: str) -> None:
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            return

        documents, _ = self.document_repo.list(
            load_id=load_id,
            page=1,
            page_size=500,
            include_related=False,
        )

        present_document_types = [document.document_type for document in documents]
        readiness = calculate_packet_readiness(document_types=present_document_types)

        load.has_ratecon = DocumentType.RATE_CONFIRMATION in present_document_types
        load.has_bol = DocumentType.BILL_OF_LADING in present_document_types
        load.has_invoice = DocumentType.INVOICE in present_document_types
        load.documents_complete = bool(readiness["ready_to_submit"])

        self.load_repo.update(load)

    def _normalize_document_type(
        self,
        value: str | DocumentType | None,
        *,
        allow_none: bool = False,
    ) -> DocumentType | None:
        if value is None:
            if allow_none:
                return None
            return DocumentType.UNKNOWN

        if isinstance(value, DocumentType):
            return value

        normalized = str(value).strip().lower()
        if not normalized:
            if allow_none:
                return None
            return DocumentType.UNKNOWN

        aliases: dict[str, DocumentType] = {
            "unknown": DocumentType.UNKNOWN,
            "rate confirmation": DocumentType.RATE_CONFIRMATION,
            "rate_confirmation": DocumentType.RATE_CONFIRMATION,
            "rate-confirmation": DocumentType.RATE_CONFIRMATION,
            "ratecon": DocumentType.RATE_CONFIRMATION,
            "rc": DocumentType.RATE_CONFIRMATION,
            "bill of lading": DocumentType.BILL_OF_LADING,
            "bill_of_lading": DocumentType.BILL_OF_LADING,
            "bill-of-lading": DocumentType.BILL_OF_LADING,
            "bol": DocumentType.BILL_OF_LADING,
            "proof of delivery": DocumentType.PROOF_OF_DELIVERY,
            "proof_of_delivery": DocumentType.PROOF_OF_DELIVERY,
            "proof-of-delivery": DocumentType.PROOF_OF_DELIVERY,
            "pod": DocumentType.PROOF_OF_DELIVERY,
            "invoice": DocumentType.INVOICE,
            "lumper receipt": DocumentType.LUMPER_RECEIPT,
            "lumper_receipt": DocumentType.LUMPER_RECEIPT,
            "detention support": DocumentType.DETENTION_SUPPORT,
            "detention_support": DocumentType.DETENTION_SUPPORT,
            "scale ticket": DocumentType.SCALE_TICKET,
            "scale_ticket": DocumentType.SCALE_TICKET,
            "accessorial support": DocumentType.ACCESSORIAL_SUPPORT,
            "accessorial_support": DocumentType.ACCESSORIAL_SUPPORT,
            "payment remittance": DocumentType.PAYMENT_REMITTANCE,
            "payment_remittance": DocumentType.PAYMENT_REMITTANCE,
            "notice of assignment": DocumentType.NOTICE_OF_ASSIGNMENT,
            "notice_of_assignment": DocumentType.NOTICE_OF_ASSIGNMENT,
            "w9": DocumentType.W9,
            "w-9": DocumentType.W9,
            "certificate of insurance": DocumentType.CERTIFICATE_OF_INSURANCE,
            "certificate_of_insurance": DocumentType.CERTIFICATE_OF_INSURANCE,
            "damage claim photo": DocumentType.DAMAGE_CLAIM_PHOTO,
            "damage_claim_photo": DocumentType.DAMAGE_CLAIM_PHOTO,
            "other": DocumentType.OTHER,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError("Invalid document_type", details={"document_type": value})

    def _normalize_processing_status(
        self,
        value: str | ProcessingStatus | None,
        *,
        allow_none: bool = False,
    ) -> ProcessingStatus | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError("processing_status is required")

        if isinstance(value, ProcessingStatus):
            return value

        normalized = str(value).strip().lower()
        if not normalized:
            if allow_none:
                return None
            raise ValidationError("processing_status is required")

        aliases: dict[str, ProcessingStatus] = {
            "pending": ProcessingStatus.PENDING,
            "processing": ProcessingStatus.IN_PROGRESS,
            "in_progress": ProcessingStatus.IN_PROGRESS,
            "in-progress": ProcessingStatus.IN_PROGRESS,
            "completed": ProcessingStatus.COMPLETED,
            "failed": ProcessingStatus.FAILED,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid processing_status",
            details={"processing_status": value},
        )

    def _normalize_channel(self, value: str | Channel) -> Channel:
        if isinstance(value, Channel):
            return value

        normalized = str(value).strip().lower()
        aliases: dict[str, Channel] = {
            "manual": Channel.MANUAL,
            "web": Channel.WEB,
            "email": Channel.EMAIL,
            "whatsapp": Channel.WHATSAPP,
            "api": Channel.API,
            "driver_portal": Channel.DRIVER_PORTAL,
            "driver-portal": Channel.DRIVER_PORTAL,
            "driver portal": Channel.DRIVER_PORTAL,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid source_channel",
            details={"source_channel": value},
        )

    @staticmethod
    def _build_file_hash(
        *,
        storage_key: str,
        file_bytes: bytes | None = None,
        original_filename: str | None = None,
        file_size_bytes: int | None = None,
    ) -> str:
        hasher = hashlib.sha256()

        if file_bytes is not None:
            hasher.update(file_bytes)
        else:
            fallback = f"{storage_key}|{original_filename}|{file_size_bytes}"
            hasher.update(fallback.encode("utf-8"))

        return hasher.hexdigest()

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str | None) -> str:
        normalized = cls._normalize_optional_text(value)
        if normalized is None:
            raise ValidationError(f"{field_name} is required")
        return normalized

    @staticmethod
    def _validate_non_negative_int(field_name: str, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValidationError(f"{field_name} cannot be negative")
        return value

    @staticmethod
    def _validate_positive_int(field_name: str, value: int) -> int:
        if value < 1:
            raise ValidationError(f"{field_name} must be greater than 0")
        return value

    @staticmethod
    def _validate_classification_confidence(value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValidationError("classification_confidence must be between 0 and 1")
        return float(value)
