from __future__ import annotations

from app.domain.enums.document_type import DocumentType
from app.services.documents.document_service import DocumentService
from app.services.loads.packet_readiness import calculate_packet_readiness


def test_packet_readiness_requires_rate_confirmation_and_pod_for_invoice() -> None:
    readiness = calculate_packet_readiness(
        document_types=[DocumentType.RATE_CONFIRMATION],
    )

    assert readiness["ready_for_invoice"] is False
    assert readiness["ready_to_submit"] is False
    assert readiness["missing_required_documents"]["invoice"] == ["proof_of_delivery"]
    assert readiness["missing_required_documents"]["submission"] == [
        "invoice",
        "proof_of_delivery",
    ]


def test_packet_readiness_ready_to_submit_with_core_submission_set() -> None:
    readiness = calculate_packet_readiness(
        document_types=[
            DocumentType.RATE_CONFIRMATION,
            DocumentType.PROOF_OF_DELIVERY,
            DocumentType.INVOICE,
        ],
    )

    assert readiness["readiness_state"] == "ready_to_submit"
    assert readiness["ready_for_invoice"] is True
    assert readiness["ready_to_submit"] is True
    assert readiness["missing_required_documents"]["submission"] == []


def test_document_type_aliases_cover_new_packet_supporting_documents(db_session) -> None:
    service = DocumentService(db_session)

    assert service._normalize_document_type("lumper_receipt") == DocumentType.LUMPER_RECEIPT
    assert service._normalize_document_type("detention support") == DocumentType.DETENTION_SUPPORT
    assert service._normalize_document_type("scale_ticket") == DocumentType.SCALE_TICKET
    assert service._normalize_document_type("accessorial_support") == DocumentType.ACCESSORIAL_SUPPORT
    assert service._normalize_document_type("payment_remittance") == DocumentType.PAYMENT_REMITTANCE
    assert service._normalize_document_type("notice_of_assignment") == DocumentType.NOTICE_OF_ASSIGNMENT
    assert service._normalize_document_type("w9") == DocumentType.W9
    assert service._normalize_document_type("certificate_of_insurance") == DocumentType.CERTIFICATE_OF_INSURANCE
    assert service._normalize_document_type("damage_claim_photo") == DocumentType.DAMAGE_CLAIM_PHOTO
