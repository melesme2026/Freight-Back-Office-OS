from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.api.v1.load_payment_reconciliation import _authorize_payment_write
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.services.loads.load_service import LoadService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService


ORG_ID = "00000000-0000-0000-0000-000000008001"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000008002"


def _make_load(db_session, *, organization_id: str = ORG_ID):
    return LoadService(db_session).create_load(
        organization_id=organization_id,
        customer_account_id="00000000-0000-0000-0000-000000009902",
        driver_id="00000000-0000-0000-0000-000000009903",
        load_number="LD-001",
        gross_amount=Decimal("1500.00"),
        currency_code="USD",
    )


def test_create_record_on_first_get(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.get_or_create_for_load(str(load.id), ORG_ID)

    assert record.load_id == load.id
    assert record.expected_amount == Decimal("1500.00")
    assert record.payment_status == LoadPaymentStatus.NOT_SUBMITTED


def test_mark_paid_sets_status_paid(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_paid(str(load.id), ORG_ID, Decimal("1500.00"), datetime.now(timezone.utc))

    assert record.payment_status == LoadPaymentStatus.PAID


def test_partial_payment_sets_partially_paid(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_partial_payment(str(load.id), ORG_ID, Decimal("500.00"))

    assert record.payment_status == LoadPaymentStatus.PARTIALLY_PAID


def test_advance_paid_sets_advance_paid(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_advance_paid(str(load.id), ORG_ID, Decimal("800.00"), datetime.now(timezone.utc), "Acme Factor")

    assert record.payment_status == LoadPaymentStatus.ADVANCE_PAID


def test_reserve_pending_logic(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_reserve_pending(str(load.id), ORG_ID, Decimal("200.00"))

    assert record.payment_status == LoadPaymentStatus.RESERVE_PENDING


def test_reserve_paid_updates_correctly(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)
    service.mark_reserve_pending(str(load.id), ORG_ID, Decimal("300.00"))

    record = service.mark_reserve_paid(str(load.id), ORG_ID, Decimal("300.00"), datetime.now(timezone.utc))

    assert record.reserve_paid_amount == Decimal("300.00")
    assert record.payment_status == LoadPaymentStatus.AWAITING_PAYMENT


def test_short_paid_calculates_delta(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_short_paid(str(load.id), ORG_ID, Decimal("1200.00"), Decimal("1500.00"), "Lumpar fee deduction")

    assert record.short_paid_amount == Decimal("300.00")
    assert record.payment_status == LoadPaymentStatus.SHORT_PAID


def test_dispute_sets_status_and_reason(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_disputed(str(load.id), ORG_ID, "Broker disputed accessorial")

    assert record.payment_status == LoadPaymentStatus.DISPUTED
    assert record.dispute_reason == "Broker disputed accessorial"


def test_driver_cannot_update() -> None:
    with pytest.raises(ForbiddenError):
        _authorize_payment_write({"role": "driver"})


def test_cross_org_denied(db_session) -> None:
    load = _make_load(db_session, organization_id=ORG_ID)
    service = PaymentReconciliationService(db_session)

    with pytest.raises(NotFoundError):
        service.get_or_create_for_load(str(load.id), OTHER_ORG_ID)
