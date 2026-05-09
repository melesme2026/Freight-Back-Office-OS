from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.api.v1.factoring_companies import _authorize_write as _authorize_factoring_company_write
from app.api.v1.load_payment_reconciliation import _authorize_payment_write
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.services.loads.load_service import LoadService
from app.services.payments.factoring_company_service import FactoringCompanyService
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

    record = service.mark_advance_paid(
        str(load.id), ORG_ID, Decimal("800.00"), datetime.now(timezone.utc), "Acme Factor"
    )

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

    record = service.mark_reserve_paid(
        str(load.id), ORG_ID, Decimal("300.00"), datetime.now(timezone.utc)
    )

    assert record.reserve_paid_amount == Decimal("300.00")
    assert record.payment_status == LoadPaymentStatus.AWAITING_PAYMENT


def test_short_paid_calculates_delta(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_short_paid(
        str(load.id), ORG_ID, Decimal("1200.00"), Decimal("1500.00"), "Lumpar fee deduction"
    )

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


def test_factoring_company_assignment_applies_defaults(db_session) -> None:
    load = _make_load(db_session)
    company = FactoringCompanyService(db_session).create_company(
        organization_id=ORG_ID,
        company_name="Blue River Capital",
        contact_email="funding@example.com",
        phone="555-0101",
        notes="Primary factor",
        default_reserve_percent="10",
        default_fee_percent="3",
    )
    service = PaymentReconciliationService(db_session)

    record = service.assign_factoring(
        str(load.id),
        ORG_ID,
        factoring_company_id=str(company.id),
        factor_name=None,
        notes="Missing paperwork cleared",
    )

    assert record.factoring_company_id == company.id
    assert record.factor_name == "Blue River Capital"
    assert record.reserve_amount == Decimal("150.00")
    assert record.factoring_fee_amount == Decimal("45.00")
    assert record.factoring_status == FactoringWorkflowStatus.SUBMITTED_TO_FACTORING
    assert record.reconciliation_status == FactoringReconciliationStatus.UNRECONCILED
    assert record.factoring_notes == "Missing paperwork cleared"


def test_factoring_advance_tracks_fee_reserve_and_partial_reconciliation(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.mark_advance_paid(
        str(load.id),
        ORG_ID,
        Decimal("1200.00"),
        datetime.now(timezone.utc),
        "Acme Factor",
        factoring_fee_percent="2.5",
        reserve_amount="250.00",
        notes="Reserve pending broker payment",
    )

    assert record.factoring_used is True
    assert record.factoring_fee_amount == Decimal("37.50")
    assert service.reserve_pending_amount(record) == Decimal("250.00")
    assert record.factoring_status == FactoringWorkflowStatus.RESERVE_PENDING
    assert record.reconciliation_status == FactoringReconciliationStatus.PARTIALLY_RECONCILED


def test_reconciliation_status_validation(db_session) -> None:
    load = _make_load(db_session)
    service = PaymentReconciliationService(db_session)

    record = service.set_reconciliation_status(str(load.id), ORG_ID, "reconciled")

    assert record.reconciliation_status == FactoringReconciliationStatus.RECONCILED
    assert record.factoring_status == FactoringWorkflowStatus.RECONCILED
    with pytest.raises(ValueError):
        service.set_reconciliation_status(str(load.id), ORG_ID, "closed")


def test_driver_cannot_modify_factoring_companies() -> None:
    with pytest.raises(ForbiddenError):
        _authorize_factoring_company_write({"role": "driver"})
