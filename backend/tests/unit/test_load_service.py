from __future__ import annotations

from decimal import Decimal

from app.domain.enums.load_status import LoadStatus
from app.services.loads.load_service import LoadService


def test_create_load_sets_defaults(db_session) -> None:
    service = LoadService(db_session)

    item = service.create_load(
        organization_id="00000000-0000-0000-0000-000000000001",
        customer_account_id="00000000-0000-0000-0000-000000000002",
        driver_id="00000000-0000-0000-0000-000000000003",
        load_number="LOAD-1001",
        gross_amount=Decimal("1250.00"),
    )

    assert item.load_number == "LOAD-1001"
    assert item.status == LoadStatus.NEW
    assert item.documents_complete is False
    assert item.gross_amount == Decimal("1250.00")


def test_attach_document_flags_marks_docs_received(db_session) -> None:
    service = LoadService(db_session)

    item = service.create_load(
        organization_id="00000000-0000-0000-0000-000000000011",
        customer_account_id="00000000-0000-0000-0000-000000000012",
        driver_id="00000000-0000-0000-0000-000000000013",
    )

    updated = service.attach_document_flags(
        load_id=str(item.id),
        has_ratecon=True,
        has_bol=True,
    )

    assert updated.has_ratecon is True
    assert updated.has_bol is True
    assert updated.documents_complete is True
    assert updated.status == LoadStatus.DOCS_RECEIVED


def test_update_extraction_confidence_sets_value(db_session) -> None:
    service = LoadService(db_session)

    item = service.create_load(
        organization_id="00000000-0000-0000-0000-000000000021",
        customer_account_id="00000000-0000-0000-0000-000000000022",
        driver_id="00000000-0000-0000-0000-000000000023",
    )

    updated = service.update_extraction_confidence(
        load_id=str(item.id),
        extraction_confidence_avg=Decimal("0.9123"),
    )

    assert updated.extraction_confidence_avg == Decimal("0.9123")
    assert updated.last_reviewed_at is not None