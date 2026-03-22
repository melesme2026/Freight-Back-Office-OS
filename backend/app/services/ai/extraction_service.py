from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.models.extracted_field import ExtractedField
from app.repositories.document_repo import DocumentRepository
from app.repositories.extracted_field_repo import ExtractedFieldRepository
from app.services.ai.confidence_service import ConfidenceService
from app.services.ai.llm_service import LLMService
from app.services.ai.ocr_service import OCRService
from app.services.documents.document_classifier import DocumentClassifier


class ExtractionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.extracted_field_repo = ExtractedFieldRepository(db)
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
        self.confidence_service = ConfidenceService()
        self.document_classifier = DocumentClassifier()

    def extract_document(
        self,
        *,
        document_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found", details={"document_id": document_id})

        if force:
            self.extracted_field_repo.delete_for_document(document.id)

        ocr_result = self.ocr_service.extract_text(
            storage_key=document.storage_key,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
        )

        detected_type, classification_confidence = self.document_classifier.classify(
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            text_content=ocr_result.get("text"),
        )

        llm_fields = self.llm_service.extract_fields(
            document_type=str(detected_type),
            text_content=ocr_result.get("text", ""),
        )

        extracted_models: list[ExtractedField] = []
        confidence_values: list[Decimal] = []

        for item in llm_fields:
            confidence = Decimal(str(item.get("confidence_score", "0.50")))
            confidence_values.append(confidence)

            extracted_models.append(
                ExtractedField(
                    organization_id=document.organization_id,
                    document_id=document.id,
                    load_id=document.load_id,
                    field_name=item["field_name"],
                    field_value_text=item.get("field_value_text"),
                    field_value_number=item.get("field_value_number"),
                    field_value_date=item.get("field_value_date"),
                    field_value_json=item.get("field_value_json"),
                    confidence_score=confidence,
                    source_model=item.get("source_model"),
                    source_engine=item.get("source_engine"),
                    is_human_corrected=False,
                    corrected_by_staff_user_id=None,
                    corrected_at=None,
                )
            )

        created_fields = self.extracted_field_repo.create_many(extracted_models)

        avg_confidence = self.confidence_service.average_decimal(confidence_values)

        document.document_type = detected_type
        document.classification_confidence = classification_confidence
        document.ocr_completed_at = datetime.now(timezone.utc)
        document.processing_status = "completed"
        self.document_repo.update(document)

        return {
            "document_id": str(document.id),
            "load_id": str(document.load_id) if document.load_id else None,
            "document_type": str(detected_type),
            "classification_confidence": Decimal(str(classification_confidence)),
            "extracted_fields": [
                {
                    "field_name": f.field_name,
                    "field_value_text": f.field_value_text,
                    "field_value_number": f.field_value_number,
                    "field_value_date": f.field_value_date,
                    "field_value_json": f.field_value_json,
                    "confidence_score": f.confidence_score,
                    "source_model": f.source_model,
                    "source_engine": f.source_engine,
                }
                for f in created_fields
            ],
            "extraction_confidence_avg": avg_confidence,
            "extracted_at": datetime.now(timezone.utc),
        }