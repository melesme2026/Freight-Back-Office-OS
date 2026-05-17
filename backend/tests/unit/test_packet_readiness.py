from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load_document import LoadDocument
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService
from app.services.loads.packet_readiness import (
    calculate_load_packet_readiness,
    calculate_organization_readiness_counts,
    calculate_packet_readiness,
    sync_load_document_readiness,
)


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


def test_document_type_aliases_cover_new_packet_supporting_documents(
    db_session,
) -> None:
    service = DocumentService(db_session)

    assert (
        service._normalize_document_type("lumper_receipt")
        == DocumentType.LUMPER_RECEIPT
    )
    assert (
        service._normalize_document_type("detention support")
        == DocumentType.DETENTION_SUPPORT
    )
    assert service._normalize_document_type("scale_ticket") == DocumentType.SCALE_TICKET
    assert (
        service._normalize_document_type("accessorial_support")
        == DocumentType.ACCESSORIAL_SUPPORT
    )
    assert (
        service._normalize_document_type("payment_remittance")
        == DocumentType.PAYMENT_REMITTANCE
    )
    assert (
        service._normalize_document_type("notice_of_assignment")
        == DocumentType.NOTICE_OF_ASSIGNMENT
    )
    assert service._normalize_document_type("w9") == DocumentType.W9
    assert (
        service._normalize_document_type("certificate_of_insurance")
        == DocumentType.CERTIFICATE_OF_INSURANCE
    )
    assert (
        service._normalize_document_type("damage_claim_photo")
        == DocumentType.DAMAGE_CLAIM_PHOTO
    )


def _create_load_for_readiness(db_session, *, load_number: str = "READY-1"):
    return LoadService(db_session).create_load(
        organization_id="00000000-0000-0000-0000-000000000601",
        customer_account_id="00000000-0000-0000-0000-000000000602",
        driver_id="00000000-0000-0000-0000-000000000603",
        load_number=load_number,
    )


def _attach_doc(
    db_session, load, document_type: DocumentType, key: str
) -> LoadDocument:
    doc = LoadDocument(
        organization_id=load.organization_id,
        customer_account_id=load.customer_account_id,
        driver_id=load.driver_id,
        load_id=load.id,
        source_channel=Channel.MANUAL,
        document_type=document_type,
        original_filename=f"{key}.pdf",
        mime_type="application/pdf",
        file_size_bytes=100,
        storage_bucket="test",
        storage_key=key,
        file_hash_sha256=f"{key:0<64}"[:64],
        page_count=1,
        processing_status=ProcessingStatus.COMPLETED,
        classification_confidence=0.99,
        ocr_completed_at=None,
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def test_pod_upload_delete_reupload_updates_canonical_readiness(db_session) -> None:
    load = _create_load_for_readiness(db_session)
    _attach_doc(db_session, load, DocumentType.RATE_CONFIRMATION, "ratecon")
    _attach_doc(db_session, load, DocumentType.INVOICE, "invoice")

    assert calculate_load_packet_readiness(load=load, db=db_session)[
        "missing_required_documents"
    ]["submission"] == ["proof_of_delivery"]

    pod = _attach_doc(db_session, load, DocumentType.PROOF_OF_DELIVERY, "pod1")
    sync_load_document_readiness(db=db_session, load_id=str(load.id))
    assert (
        calculate_load_packet_readiness(load=load, db=db_session)[
            "missing_required_documents"
        ]["submission"]
        == []
    )

    db_session.delete(pod)
    db_session.flush()
    sync_load_document_readiness(db=db_session, load_id=str(load.id))
    assert calculate_load_packet_readiness(load=load, db=db_session)[
        "missing_required_documents"
    ]["submission"] == ["proof_of_delivery"]

    _attach_doc(db_session, load, DocumentType.PROOF_OF_DELIVERY, "pod2")
    sync_load_document_readiness(db=db_session, load_id=str(load.id))
    assert (
        calculate_load_packet_readiness(load=load, db=db_session)[
            "missing_required_documents"
        ]["submission"]
        == []
    )


def test_stale_flags_cannot_override_actual_documents(db_session) -> None:
    load = _create_load_for_readiness(db_session, load_number="STALE-1")
    load.has_ratecon = False
    load.has_bol = False
    load.has_invoice = False
    load.documents_complete = False
    _attach_doc(db_session, load, DocumentType.RATE_CONFIRMATION, "stale-ratecon")
    _attach_doc(db_session, load, DocumentType.PROOF_OF_DELIVERY, "stale-pod")
    _attach_doc(db_session, load, DocumentType.INVOICE, "stale-invoice")
    db_session.flush()

    readiness = calculate_load_packet_readiness(load=load, db=db_session)

    assert readiness["ready_to_submit"] is True
    assert readiness["missing_required_documents"]["submission"] == []


def test_dashboard_counts_match_canonical_load_readiness(db_session) -> None:
    ready = _create_load_for_readiness(db_session, load_number="DASH-READY")
    missing = _create_load_for_readiness(db_session, load_number="DASH-MISSING")
    _attach_doc(db_session, ready, DocumentType.RATE_CONFIRMATION, "dash-ratecon")
    _attach_doc(db_session, ready, DocumentType.PROOF_OF_DELIVERY, "dash-pod")
    _attach_doc(db_session, ready, DocumentType.INVOICE, "dash-invoice")
    _attach_doc(
        db_session, missing, DocumentType.RATE_CONFIRMATION, "dash-missing-ratecon"
    )
    db_session.flush()

    counts = calculate_organization_readiness_counts(
        db=db_session, organization_id=str(ready.organization_id)
    )

    assert counts["loads_ready_to_submit"] == 1
    assert counts["loads_missing_documents"] == 1
