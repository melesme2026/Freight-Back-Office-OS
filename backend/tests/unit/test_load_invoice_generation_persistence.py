from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.api.v1.loads import (
    _build_load_packet_readiness,
    _generate_and_persist_invoice_pdf,
    download_load_invoice,
)
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.services.carrier_profile_service import CarrierProfileService
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.load_service import LoadService
from app.services.loads.operational_queue_service import OperationalQueueService
from app.services.loads.packet_readiness import calculate_packet_readiness


async def _read_streaming_response_bytes(response) -> bytes:
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)


def _create_ready_for_invoice_load(db_session):
    load_service = LoadService(db_session)
    document_service = DocumentService(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000451",
        customer_account_id="00000000-0000-0000-0000-000000000452",
        driver_id="00000000-0000-0000-0000-000000000453",
        load_number="INV-451",
    )

    CarrierProfileService(db_session).upsert_profile(
        str(load.organization_id),
        {
            "legal_name": "Blue Sky Transport LLC",
            "address_line1": "100 Main St",
            "address_line2": "Suite 200",
            "city": "Chicago",
            "state": "IL",
            "zip": "60601",
            "country": "USA",
            "phone": "+1-555-111-2222",
            "email": "billing@bluesky.example",
            "mc_number": "MC-778899",
            "dot_number": "DOT-112233",
            "remit_to_name": "Blue Sky Transport LLC",
            "remit_to_address": "100 Main St, Suite 200, Chicago, IL 60601",
            "remit_to_notes": "ACH preferred",
        },
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
    assert invoice_documents[0].processing_status == ProcessingStatus.COMPLETED
    assert invoice_documents[0].received_at is not None
    assert invoice_documents[0].file_size_bytes == len(pdf_bytes)
    assert storage_service.read_bytes(relative_path=invoice_documents[0].storage_key) == pdf_bytes
    assert b"Freight Invoice" in pdf_bytes
    assert f"Load #: {load.load_number}".encode("latin-1") in pdf_bytes
    assert b"Broker / Factor Packet Checklist" in pdf_bytes


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
    all_documents, all_total = document_service.list_documents(
        load_id=str(load.id),
        page=1,
        page_size=25,
    )

    assert first_response.media_type == "application/pdf"
    assert second_response.media_type == "application/pdf"
    assert total == 1
    assert len(invoice_documents) == 1
    assert invoice_documents[0].document_type == DocumentType.INVOICE
    assert invoice_documents[0].processing_status == ProcessingStatus.COMPLETED
    assert str(invoice_documents[0].load_id) == str(load.id)
    assert all_total == 3
    assert DocumentType.INVOICE in {document.document_type for document in all_documents}

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


def test_download_invoice_route_returns_professional_invoice_sections(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    token_payload = {
        "organization_id": str(load.organization_id),
        "role": "staff",
    }

    response = download_load_invoice(
        load_id=load.id,
        token_payload=token_payload,
        db=db_session,
    )
    pdf_bytes = asyncio.run(_read_streaming_response_bytes(response))

    assert response.media_type == "application/pdf"
    assert b"Freight Invoice" in pdf_bytes
    assert b"Carrier / Remit-To" in pdf_bytes
    assert b"Bill-To / Broker" in pdf_bytes
    assert b"Shipment Details" in pdf_bytes
    assert b"Charges" in pdf_bytes
    assert b"Broker / Factor Packet Checklist" in pdf_bytes
    assert b"Please reference invoice number and load number with payment." in pdf_bytes


def test_generate_invoice_logs_template_selection(db_session, caplog) -> None:
    load = _create_ready_for_invoice_load(db_session)
    caplog.set_level(logging.INFO)

    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    assert "USING TEMPLATE: _build_professional_invoice_pdf" in caplog.text


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


def test_invoice_status_reports_existing_invoice_and_staleness(db_session) -> None:
    from app.api.v1.loads import _serialize_invoice_status

    load = _create_ready_for_invoice_load(db_session)
    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    fresh_status = _serialize_invoice_status(db=db_session, load=load)
    assert fresh_status["has_invoice"] is True
    assert fresh_status["invoice_number"] == load.invoice_number
    assert fresh_status["is_stale"] is False

    LoadService(db_session).update_load(load_id=str(load.id), gross_amount="2250.00")
    refreshed = LoadService(db_session).get_load(str(load.id))
    refreshed.updated_at = datetime.now(timezone.utc) + timedelta(seconds=5)
    db_session.add(refreshed)
    db_session.flush()
    stale_status = _serialize_invoice_status(db=db_session, load=refreshed)

    assert stale_status["has_invoice"] is True
    assert stale_status["is_stale"] is True
    assert any("Load amount" in reason for reason in stale_status["stale_reasons"])


def test_regenerate_replaces_pdf_without_changing_invoice_number_or_duplicating(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    document_service = DocumentService(db_session)

    _generate_and_persist_invoice_pdf(db=db_session, load=load)
    invoice_number = load.invoice_number
    LoadService(db_session).update_load(load_id=str(load.id), notes="Updated invoice note")
    refreshed = LoadService(db_session).get_load(str(load.id))

    regenerated_pdf = _generate_and_persist_invoice_pdf(
        db=db_session,
        load=refreshed,
        force_regenerate=True,
    )
    documents, total = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )

    assert total == 1
    assert refreshed.invoice_number == invoice_number
    assert b"Updated invoice note" in regenerated_pdf
    assert len(documents) == 1
    assert documents[0].processing_status == ProcessingStatus.COMPLETED


def test_invoice_route_regenerate_requires_explicit_flag_to_replace_stale_pdf(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    token_payload = {"organization_id": str(load.organization_id), "role": "staff"}

    first_response = download_load_invoice(load_id=load.id, token_payload=token_payload, db=db_session)
    first_pdf = asyncio.run(_read_streaming_response_bytes(first_response))
    LoadService(db_session).update_load(load_id=str(load.id), notes="Regenerated only with confirmation")

    stale_view_response = download_load_invoice(
        load_id=load.id,
        token_payload=token_payload,
        db=db_session,
    )
    stale_view_pdf = asyncio.run(_read_streaming_response_bytes(stale_view_response))
    explicit_regen_response = download_load_invoice(
        load_id=load.id,
        regenerate=True,
        token_payload=token_payload,
        db=db_session,
    )
    explicit_regen_pdf = asyncio.run(_read_streaming_response_bytes(explicit_regen_response))

    assert stale_view_pdf == first_pdf
    assert b"Regenerated only with" in explicit_regen_pdf


def test_document_delete_reupload_recomputes_canonical_readiness(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    _generate_and_persist_invoice_pdf(db=db_session, load=load)
    document_service = DocumentService(db_session)

    pod_documents, _ = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.PROOF_OF_DELIVERY,
        page=1,
        page_size=25,
    )
    document_service.delete_document(document_id=str(pod_documents[0].id))
    db_session.flush()

    missing_readiness = _build_load_packet_readiness(load, db=db_session)
    assert DocumentType.PROOF_OF_DELIVERY.value in missing_readiness["missing_required_documents"]["submission"]

    document_service.create_document(
        organization_id=str(load.organization_id),
        customer_account_id=str(load.customer_account_id),
        driver_id=str(load.driver_id),
        load_id=str(load.id),
        document_type="signed_pod",
        source_channel="driver_portal",
        storage_key="uploads/reuploaded-signed-pod.pdf",
        original_filename="reuploaded-signed-pod.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
    )
    db_session.flush()

    reuploaded_readiness = _build_load_packet_readiness(load, db=db_session)
    assert DocumentType.PROOF_OF_DELIVERY.value in reuploaded_readiness["present_documents"]
    assert DocumentType.PROOF_OF_DELIVERY.value not in reuploaded_readiness["missing_required_documents"]["submission"]
    assert reuploaded_readiness["ready_to_submit"] is True

    invoice_documents, _ = document_service.list_documents(
        load_id=str(load.id),
        document_type=DocumentType.INVOICE,
        page=1,
        page_size=25,
    )
    assert len(invoice_documents) == 1
    assert invoice_documents[0].processing_status == ProcessingStatus.COMPLETED


def test_actual_documents_override_stale_missing_snapshot_and_flags(db_session) -> None:
    load = _create_ready_for_invoice_load(db_session)
    _generate_and_persist_invoice_pdf(db=db_session, load=load)

    stale_projection = SimpleNamespace(
        id=load.id,
        documents=None,
        has_ratecon=False,
        has_bol=False,
        has_invoice=False,
        required_documents_missing=[DocumentType.PROOF_OF_DELIVERY.value],
        packet_readiness={
            "missing_required_documents": {
                "submission": [DocumentType.PROOF_OF_DELIVERY.value]
            }
        },
    )

    readiness = _build_load_packet_readiness(stale_projection, db=db_session)

    assert readiness["ready_to_submit"] is True
    assert DocumentType.PROOF_OF_DELIVERY.value in readiness["present_documents"]
    assert readiness["missing_required_documents"]["submission"] == []


def test_staff_and_driver_serializers_share_canonical_readiness(db_session) -> None:
    from app.api.v1.loads import _serialize_load

    load = _create_ready_for_invoice_load(db_session)
    _generate_and_persist_invoice_pdf(db=db_session, load=load)
    load.has_ratecon = False
    load.has_invoice = False
    load.documents_complete = False
    db_session.add(load)
    db_session.flush()

    staff_payload = _serialize_load(load, detailed=True, db=db_session)
    driver_payload = _serialize_load(load, detailed=False, db=db_session)

    assert staff_payload["packet_readiness"] == driver_payload["packet_readiness"]
    assert staff_payload["packet_readiness"]["ready_to_submit"] is True
    assert staff_payload["packet_readiness"]["missing_required_documents"]["submission"] == []
