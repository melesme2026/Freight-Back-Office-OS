from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace

import pytest

from app.api.v1.loads import _authorize_submission_download, _authorize_submission_write
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.enums.document_type import DocumentType
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.load_service import LoadService
from app.services.loads.submission_packet_service import SubmissionPacketService


def _seed_load_with_docs(db_session, *, organization_id: str, include_invoice: bool = True):
    load = LoadService(db_session).create_load(
        organization_id=organization_id,
        customer_account_id="00000000-0000-0000-0000-000000009902",
        driver_id="00000000-0000-0000-0000-000000009903",
        load_number="LD-001",
    )
    doc_service = DocumentService(db_session)
    required = [DocumentType.RATE_CONFIRMATION, DocumentType.PROOF_OF_DELIVERY]
    if include_invoice:
        required.append(DocumentType.INVOICE)
    required.append(DocumentType.BILL_OF_LADING)

    for idx, doc_type in enumerate(required, start=1):
        doc_service.create_document(
            organization_id=organization_id,
            customer_account_id="00000000-0000-0000-0000-000000009902",
            driver_id="00000000-0000-0000-0000-000000009903",
            load_id=str(load.id),
            source_channel="manual",
            document_type=doc_type,
            storage_key=f"uploads/submission-{idx}.pdf",
            original_filename=f"submission-{idx}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1000 + idx,
        )
    return load


def test_create_packet_fails_when_required_documents_missing(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009901", include_invoice=False)

    service = SubmissionPacketService(db_session)
    with pytest.raises(ValidationError) as exc:
        service.create_packet_from_load(str(load.id), "00000000-0000-0000-0000-000000009901", None)

    assert exc.value.details["missing_documents"] == [DocumentType.INVOICE.value]


def test_create_packet_succeeds_and_snapshots_documents(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009911")

    packet = SubmissionPacketService(db_session).create_packet_from_load(
        str(load.id),
        "00000000-0000-0000-0000-000000009911",
        "00000000-0000-0000-0000-000000009999",
    )

    assert packet.status == "ready"
    assert len(packet.documents) == 4
    doc_types = {doc.document_type for doc in packet.documents}
    assert DocumentType.INVOICE.value in doc_types
    assert DocumentType.RATE_CONFIRMATION.value in doc_types
    assert DocumentType.PROOF_OF_DELIVERY.value in doc_types


def test_mark_sent_accepted_rejected_create_events(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009921")
    service = SubmissionPacketService(db_session)
    packet = service.create_packet_from_load(str(load.id), "00000000-0000-0000-0000-000000009921", None)

    sent = service.mark_sent(
        str(packet.id),
        str(load.id),
        "00000000-0000-0000-0000-000000009921",
        {"destination_type": "broker", "destination_name": "Broker", "destination_email": "billing@broker.test"},
        None,
    )
    assert sent.status == "sent"
    assert sent.sent_at is not None
    assert any(event.event_type == "packet_sent" for event in sent.events)

    accepted = service.mark_accepted(str(packet.id), str(load.id), "00000000-0000-0000-0000-000000009921", None)
    assert accepted.status == "accepted"
    assert any(event.event_type == "packet_accepted" for event in accepted.events)

    rejected = service.mark_rejected(
        str(packet.id),
        str(load.id),
        "00000000-0000-0000-0000-000000009921",
        "Missing signature",
        None,
        resubmission_required=True,
    )
    assert rejected.status == "resubmission_required"
    assert any(event.event_type == "resubmission_requested" for event in rejected.events)


def test_cross_org_access_denied(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009931")
    service = SubmissionPacketService(db_session)
    packet = service.create_packet_from_load(str(load.id), "00000000-0000-0000-0000-000000009931", None)

    with pytest.raises(NotFoundError):
        service.get_packet(str(packet.id), str(load.id), "00000000-0000-0000-0000-000000009932")


def test_driver_cannot_create_or_mark_packets() -> None:
    with pytest.raises(ForbiddenError):
        _authorize_submission_write({"role": "driver"})


def test_build_packet_zip_success(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009941")
    packet = SubmissionPacketService(db_session).create_packet_from_load(
        str(load.id),
        "00000000-0000-0000-0000-000000009941",
        None,
    )
    storage = StorageService()
    for packet_doc in packet.documents:
        linked_document = packet_doc.document
        storage.save_bytes(
            relative_path=linked_document.storage_key,
            content=f"file-{packet_doc.document_type}".encode("utf-8"),
            overwrite=True,
        )

    zip_bytes, load_number = SubmissionPacketService(db_session).build_packet_zip(
        packet_id=str(packet.id),
        load_id=str(load.id),
        org_id="00000000-0000-0000-0000-000000009941",
    )

    assert load_number == "LD-001"
    assert zip_bytes


def test_build_packet_zip_contains_expected_files(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009951")
    packet = SubmissionPacketService(db_session).create_packet_from_load(
        str(load.id),
        "00000000-0000-0000-0000-000000009951",
        None,
    )
    storage = StorageService()
    for packet_doc in packet.documents:
        linked_document = packet_doc.document
        storage.save_bytes(
            relative_path=linked_document.storage_key,
            content=b"packet-document",
            overwrite=True,
        )

    zip_bytes, _ = SubmissionPacketService(db_session).build_packet_zip(
        packet_id=str(packet.id),
        load_id=str(load.id),
        org_id="00000000-0000-0000-0000-000000009951",
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
    assert names == {
        "invoice-LD-001.pdf",
        "rate-confirmation-LD-001.pdf",
        "pod-LD-001.pdf",
        "bol-LD-001.pdf",
    }


def test_submission_packet_download_cross_org_access_denied() -> None:
    with pytest.raises(ForbiddenError):
        _authorize_submission_download(
            item=SimpleNamespace(organization_id="00000000-0000-0000-0000-000000009961"),
            token_payload={
                "organization_id": "00000000-0000-0000-0000-000000009962",
                "role": "owner",
            },
        )


def test_submission_packet_download_driver_access_denied() -> None:
    with pytest.raises(ForbiddenError):
        _authorize_submission_download(
            item=SimpleNamespace(organization_id="00000000-0000-0000-0000-000000009971"),
            token_payload={
                "organization_id": "00000000-0000-0000-0000-000000009971",
                "role": "driver",
            },
        )


def test_submission_packet_download_missing_packet_returns_not_found(db_session) -> None:
    load = _seed_load_with_docs(db_session, organization_id="00000000-0000-0000-0000-000000009981")

    with pytest.raises(NotFoundError):
        SubmissionPacketService(db_session).build_packet_zip(
            packet_id="00000000-0000-0000-0000-000000000001",
            load_id=str(load.id),
            org_id="00000000-0000-0000-0000-000000009981",
        )
