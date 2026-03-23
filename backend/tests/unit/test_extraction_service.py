from __future__ import annotations

from app.services.ai.confidence_service import ConfidenceService
from app.services.ai.llm_service import LLMService
from app.services.ai.ocr_service import OCRService
from app.services.documents.document_classifier import DocumentClassifier


def test_document_classifier_detects_rate_confirmation() -> None:
    classifier = DocumentClassifier()

    document_type, confidence = classifier.classify(
        original_filename="rate_confirmation_123.pdf",
        mime_type="application/pdf",
        text_content="Rate Confirmation for load 123",
    )

    assert str(document_type) == "rate_confirmation"
    assert confidence > 0.9


def test_document_classifier_detects_invoice() -> None:
    classifier = DocumentClassifier()

    document_type, confidence = classifier.classify(
        original_filename="invoice_555.pdf",
        mime_type="application/pdf",
        text_content="Invoice Number 555",
    )

    assert str(document_type) == "invoice"
    assert confidence > 0.9


def test_ocr_service_returns_placeholder_text() -> None:
    service = OCRService()

    result = service.extract_text(
        storage_key="docs/sample.pdf",
        original_filename="sample.pdf",
        mime_type="application/pdf",
    )

    assert "text" in result
    assert "sample.pdf" in result["text"]
    assert result["pages"] == 1


def test_llm_service_returns_invoice_fields() -> None:
    service = LLMService()

    result = service.extract_fields(
        document_type="invoice",
        text_content="Invoice Number 123",
    )

    assert len(result) >= 1
    assert result[0]["field_name"] == "document_type"
    assert result[0]["field_value_text"] == "invoice"


def test_confidence_service_averages_values() -> None:
    service = ConfidenceService()

    result = service.average_decimal([])

    assert result is None