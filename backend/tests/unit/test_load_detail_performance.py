from __future__ import annotations

import uuid

from app.api.v1 import loads as loads_api
from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load import Load


def test_load_serializer_uses_document_table_over_stale_flags(db_session) -> None:
    load = Load(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_account_id=uuid.uuid4(),
        driver_id=uuid.uuid4(),
        source_channel=Channel.MANUAL,
        status=LoadStatus.INVOICE_READY,
        processing_status=ProcessingStatus.PENDING,
        load_number="PERF-LOAD-1",
        currency_code="USD",
        documents_complete=True,
        has_ratecon=True,
        has_bol=False,
        has_invoice=True,
    )

    payload = loads_api._serialize_load(load, detailed=True, db=db_session)

    assert payload["packet_readiness"]["ready_for_invoice"] is False
    assert (
        "proof_of_delivery"
        in payload["packet_readiness"]["missing_required_documents"]["invoice"]
    )
    assert payload["packet_readiness"]["present_documents"] == []


import time
from datetime import datetime, timezone

from app.api.v1 import documents as documents_api
from app.domain.enums.document_type import DocumentType
from app.domain.models.load_document import LoadDocument

PERFORMANCE_BUDGETS_MS = {
    "load_detail": 1000,
    "documents_endpoint": 500,
    "upload_response": 800,
}


def test_load_detail_serializer_stays_under_ci_budget(db_session) -> None:
    load = Load(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_account_id=uuid.uuid4(),
        driver_id=uuid.uuid4(),
        source_channel=Channel.MANUAL,
        status=LoadStatus.INVOICE_READY,
        processing_status=ProcessingStatus.PENDING,
        load_number="PERF-BUDGET-1",
        currency_code="USD",
        documents_complete=False,
        has_ratecon=True,
        has_bol=True,
        has_invoice=True,
    )

    started_at = time.perf_counter()
    payload = loads_api._serialize_load(load, detailed=True, db=db_session)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert payload["id"] == str(load.id)
    assert elapsed_ms < PERFORMANCE_BUDGETS_MS["load_detail"]


def test_documents_serializer_stays_lightweight_and_under_ci_budget() -> None:
    document = LoadDocument(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_account_id=uuid.uuid4(),
        load_id=uuid.uuid4(),
        source_channel=Channel.MANUAL,
        document_type=DocumentType.INVOICE,
        original_filename="invoice.pdf",
        storage_key="uploaded/invoice.pdf",
        file_hash_sha256="a" * 64,
        received_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.QUEUED,
    )

    started_at = time.perf_counter()
    payload = documents_api._serialize_lightweight_document(document)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert payload == {
        "id": str(document.id),
        "filename": "invoice.pdf",
        "type": "invoice",
        "uploaded_at": document.received_at.isoformat(),
        "status": "queued",
    }
    assert set(payload) == {"id", "filename", "type", "uploaded_at", "status"}
    assert elapsed_ms < PERFORMANCE_BUDGETS_MS["documents_endpoint"]


def test_upload_response_serializer_stays_lightweight_and_under_ci_budget() -> None:
    document = LoadDocument(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_account_id=uuid.uuid4(),
        load_id=uuid.uuid4(),
        source_channel=Channel.MANUAL,
        document_type=DocumentType.PROOF_OF_DELIVERY,
        original_filename="pod.png",
        storage_key="uploaded/pod.png",
        file_hash_sha256="b" * 64,
        received_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.QUEUED,
    )

    started_at = time.perf_counter()
    payload = documents_api._serialize_lightweight_document(document)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert payload["filename"] == "pod.png"
    assert set(payload) == {"id", "filename", "type", "uploaded_at", "status"}
    assert elapsed_ms < PERFORMANCE_BUDGETS_MS["upload_response"]
