from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateRecordError, NotFoundError, ValidationError
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load_document import LoadDocument
from app.repositories.document_repo import DocumentRepository


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.document_repo = DocumentRepository(db)

    def create_document(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        storage_key: str,
        source_channel: str,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_type: str | None = None,
        original_filename: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        storage_bucket: str | None = None,
        page_count: int | None = None,
        uploaded_by_staff_user_id: str | None = None,
        file_bytes: bytes | None = None,
    ) -> LoadDocument:
        normalized_document_type = self._normalize_document_type(document_type)
        validated_file_size_bytes = self._validate_non_negative_int(
            "file_size_bytes",
            file_size_bytes,
        )
        validated_page_count = self._validate_non_negative_int("page_count", page_count)

        file_hash_sha256 = self._build_file_hash(
            storage_key=storage_key,
            file_bytes=file_bytes,
            original_filename=original_filename,
            file_size_bytes=validated_file_size_bytes,
        )

        existing = self.document_repo.get_by_file_hash(file_hash_sha256=file_hash_sha256)
        if existing is not None:
            raise DuplicateRecordError(
                "Document with the same file hash already exists",
                details={
                    "document_id": str(existing.id),
                    "file_hash_sha256": file_hash_sha256,
                },
            )

        model = LoadDocument(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            source_channel=source_channel,
            document_type=normalized_document_type,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=validated_file_size_bytes,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            file_hash_sha256=file_hash_sha256,
            page_count=validated_page_count,
            processing_status=ProcessingStatus.PENDING,
            classification_confidence=None,
            ocr_completed_at=None,
            received_at=datetime.now(timezone.utc),
            uploaded_by_staff_user_id=uploaded_by_staff_user_id,
        )
        return self.document_repo.create(model)

    def get_document(self, document_id: str) -> LoadDocument:
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found", details={"document_id": document_id})
        return document

    def list_documents(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_type: str | None = None,
        processing_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[LoadDocument], int]:
        normalized_document_type = self._normalize_document_type(document_type, allow_none=True)
        normalized_processing_status = self._normalize_processing_status(
            processing_status,
            allow_none=True,
        )

        return self.document_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            processing_status=normalized_processing_status,
            page=page,
            page_size=page_size,
        )

    def mark_processing(
        self,
        *,
        document_id: str,
        processing_status: str,
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

        return self.document_repo.update(document)

    def update_document_type(
        self,
        *,
        document_id: str,
        document_type: str,
        classification_confidence: float | None = None,
    ) -> LoadDocument:
        document = self.get_document(document_id)
        normalized_document_type = self._normalize_document_type(document_type)

        document.document_type = normalized_document_type

        if classification_confidence is not None:
            document.classification_confidence = self._validate_classification_confidence(
                classification_confidence
            )

        return self.document_repo.update(document)

    def attach_to_load(
        self,
        *,
        document_id: str,
        load_id: str,
    ) -> LoadDocument:
        document = self.get_document(document_id)
        document.load_id = load_id
        return self.document_repo.update(document)

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

        return {
            "document_id": str(document.id),
            "queued": True,
            "force_reclassification": force_reclassification,
            "force_reextraction": force_reextraction,
        }

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

        aliases: dict[str, DocumentType] = {
            "unknown": DocumentType.UNKNOWN,
            "rate_confirmation": DocumentType.RATE_CONFIRMATION,
            "rateconfirmation": DocumentType.RATE_CONFIRMATION,
            "ratecon": DocumentType.RATE_CONFIRMATION,
            "bill_of_lading": DocumentType.BILL_OF_LADING,
            "billoflading": DocumentType.BILL_OF_LADING,
            "bol": DocumentType.BILL_OF_LADING,
            "proof_of_delivery": DocumentType.PROOF_OF_DELIVERY,
            "proofofdelivery": DocumentType.PROOF_OF_DELIVERY,
            "pod": DocumentType.PROOF_OF_DELIVERY,
            "invoice": DocumentType.INVOICE,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid document_type",
            details={"document_type": value},
        )

    def _normalize_processing_status(
        self,
        value: str | ProcessingStatus | None,
        *,
        allow_none: bool = False,
    ) -> ProcessingStatus | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                "processing_status is required",
                details={"processing_status": value},
            )

        if isinstance(value, ProcessingStatus):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, ProcessingStatus] = {
            "pending": ProcessingStatus.PENDING,
            "not_started": ProcessingStatus.PENDING,
            "processing": ProcessingStatus.IN_PROGRESS,
            "in_progress": ProcessingStatus.IN_PROGRESS,
            "inprogress": ProcessingStatus.IN_PROGRESS,
            "completed": ProcessingStatus.COMPLETED,
            "complete": ProcessingStatus.COMPLETED,
            "failed": ProcessingStatus.FAILED,
            "error": ProcessingStatus.FAILED,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid processing_status",
            details={"processing_status": value},
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
            fingerprint = f"{storage_key}|{original_filename or ''}|{file_size_bytes or 0}"
            hasher.update(fingerprint.encode("utf-8"))

        return hasher.hexdigest()

    @staticmethod
    def _validate_non_negative_int(field_name: str, value: int | None) -> int | None:
        if value is None:
            return None

        if value < 0:
            raise ValidationError(
                f"{field_name} cannot be negative",
                details={field_name: value},
            )

        return value

    @staticmethod
    def _validate_classification_confidence(value: float) -> float:
        confidence = float(value)

        if confidence < 0.0 or confidence > 1.0:
            raise ValidationError(
                "classification_confidence must be between 0.0 and 1.0",
                details={"classification_confidence": value},
            )

        return confidence