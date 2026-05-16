from __future__ import annotations

import uuid

from app.api.v1 import loads as loads_api
from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load import Load


def test_load_serializer_uses_flags_without_document_table_fallback(monkeypatch, db_session) -> None:
    def fail_document_lookup(*_args, **_kwargs):  # pragma: no cover - only called on regression
        raise AssertionError("core load serialization must not query documents table")

    monkeypatch.setattr(loads_api.DocumentService, "list_documents", fail_document_lookup)

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
    assert "proof_of_delivery" in payload["packet_readiness"]["missing_required_documents"]["invoice"]
    assert "rate_confirmation" in payload["packet_readiness"]["present_documents"]
    assert "invoice" in payload["packet_readiness"]["present_documents"]
