from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.loads import _generate_and_persist_invoice_pdf, download_load_invoice
from app.api.v1.loads import _build_load_packet_readiness
from app.domain.enums.document_type import DocumentType
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.load_service import LoadService
from app.services.loads.operational_queue_service import OperationalQueueService
from app.services.loads.packet_readiness import calculate_packet_readiness


def _create_ready_for_invoice_load(db_session):
    load_service = LoadService(db_session)
    document_service = DocumentService(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000451",
        customer_account_id="00000000-0000-0000-0000-000000000452",
        driver_id="00000000-0000-0000-0000-000000000453",
        load_number="INV-451",
    )

    for index, document_type in enumerate(
        [DocumentType.RATE_CONFIRMATION, DocumentType.PROOF_OF_DELIVERY],
        start=1,
    ):
        document_service.create_document(
            organization_id=str(load.organization_id),
            customer_account_id=str(load.customer_account_id),
            driver_id=str(load.driver_id),
            load_id=str(load.id),
            document_type=document_type,
            source_channel="manual",
            storage_key=f"uploads/invoice-seed-{index}.pdf",
            original_filename=f"invoice-seed-{index}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024 + index,
        )

    db_session.flush()
    db_session.refresh(load)
    return load


def test_generate_invoice_creates_invoice_document(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    document_service = DocumentService(db_session)
    storage_service = StorageService()

    pdf_bytes = _generate_and_persist_invoice_pdf(db=db_session, load=load)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

    invoice_documents, total = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )
    assert total == 1
    assert len(invoice_documents) == 1
    assert invoice_documents[0].load_id == load.id
    assert storage_service.read_bytes(relative_path=invoice_documents[0].storage_key) == pdf_bytes


def test_generate_invoice_updates_has_invoice_and_readiness(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    load_service = LoadService(db_session)

    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    refreshed = load_service.get_load(str(load.id))
    assert refreshed.has_invoice is True
    assert refreshed.documents_complete is True

    readiness = calculate_packet_readiness(
        document_types=[
            document.document_type
            for document in refreshed.documents
            if document.document_type is not None
        ]
    )
    assert readiness["ready_to_submit"] is True
    assert DocumentType.INVOICE.value not in readiness["missing_required_documents"]["submission"]


def test_generate_invoice_reuses_existing_invoice_document(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    document_service = DocumentService(db_session)

    first_pdf_bytes = _generate_and_persist_invoice_pdf(db=db_session, load=load)
    initial_documents, total_initial = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )
    initial_document_id = str(initial_documents[0].id)

    second_pdf_bytes = _generate_and_persist_invoice_pdf(db=db_session, load=load)
    final_documents, total_final = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )

    assert total_initial == 1
    assert total_final == 1
    assert str(final_documents[0].id) == initial_document_id
    assert first_pdf_bytes != b""
    assert second_pdf_bytes != b""


def test_generate_invoice_clears_missing_invoice_next_action(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    load_service = LoadService(db_session)
    queue_service = OperationalQueueService()

    before = queue_service.evaluate_load(load)
    assert before["next_action"]["code"] == "generate_invoice"

    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    refreshed = load_service.get_load(str(load.id))
    after = queue_service.evaluate_load(refreshed)
    readiness = calculate_packet_readiness(
        document_types=[
            document.document_type
            for document in refreshed.documents
            if document.document_type is not None
        ]
    )

    assert refreshed.has_invoice is True
    assert DocumentType.INVOICE.value not in readiness["missing_required_documents"]["submission"]
    assert after["next_action"]["code"] != "generate_invoice"


def test_download_invoice_route_persists_invoice_and_reuses_existing_document(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    document_service = DocumentService(db_session)
    queue_service = OperationalQueueService()

    token_payload = {
        "organization_id": str(load.organization_id),
        "role": "staff",
    }

    first_response = download_load_invoice(
        load_id=load.id,
        token_payload=token_payload,
        db=db_session,
    )
    second_response = download_load_invoice(
        load_id=load.id,
        token_payload=token_payload,
        db=db_session,
    )

    invoice_documents, total = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )

    assert first_response.media_type == "application/pdf"
    assert second_response.media_type == "application/pdf"
    assert total == 1
    assert len(invoice_documents) == 1
    assert invoice_documents[0].document_type == DocumentType.INVOICE
    assert str(invoice_documents[0].load_id) == str(load.id)

    refreshed_load = LoadService(db_session).get_load(str(load.id))
    after = queue_service.evaluate_load(refreshed_load)
    readiness = calculate_packet_readiness(
        document_types=[
            document.document_type
            for document in refreshed_load.documents
            if document.document_type is not None
        ]
    )

    assert refreshed_load.has_invoice is True
    assert DocumentType.INVOICE.value not in readiness["missing_required_documents"]["submission"]
    assert after["next_action"]["code"] != "generate_invoice"


def test_packet_readiness_uses_documents_table_not_flags(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    stale_flag_snapshot = SimpleNamespace(
        id=load.id,
        documents=None,
        has_ratecon=False,
        has_bol=False,
        has_invoice=False,
    )

    readiness = _build_load_packet_readiness(stale_flag_snapshot, db=db_session)

    assert DocumentType.INVOICE.value in readiness["present_documents"]
    assert DocumentType.INVOICE.value not in readiness["missing_required_documents"]["submission"]
