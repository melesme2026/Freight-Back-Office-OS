from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import uuid
from decimal import Decimal

import pytest

from app.api.v1.reports import _authorize_reports_read
from app.core.exceptions import ForbiddenError
from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.broker import Broker
from app.domain.models.driver import Driver
from app.services.loads.load_service import LoadService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService
from app.services.reports.operational_analytics_service import OperationalAnalyticsService

ORG_ID = "00000000-0000-0000-0000-000000008101"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000008102"
CUSTOMER_ID = "00000000-0000-0000-0000-000000009901"
DRIVER_ID = "00000000-0000-0000-0000-000000009911"
DRIVER_2_ID = "00000000-0000-0000-0000-000000009912"
BROKER_ID = "00000000-0000-0000-0000-000000009921"
BROKER_2_ID = "00000000-0000-0000-0000-000000009922"


def _seed_parties(db_session):
    db_session.add_all(
        [
            Driver(id=uuid.UUID(DRIVER_ID), organization_id=ORG_ID, customer_account_id=CUSTOMER_ID, full_name="Ava Driver", phone="555-0101"),
            Driver(id=uuid.UUID(DRIVER_2_ID), organization_id=ORG_ID, customer_account_id=CUSTOMER_ID, full_name="Ben Driver", phone="555-0102"),
            Broker(id=uuid.UUID(BROKER_ID), organization_id=ORG_ID, name="Prime Broker", mc_number="MC1"),
            Broker(id=uuid.UUID(BROKER_2_ID), organization_id=ORG_ID, name="Fast Broker", mc_number="MC2"),
        ]
    )
    db_session.flush()


def _make_load(
    db_session,
    *,
    load_number: str,
    driver_id: str = DRIVER_ID,
    broker_id: str = BROKER_ID,
    pickup_date: date | None = None,
    delivery_date: date | None = None,
    pickup_location: str = "Dallas, TX",
    delivery_location: str = "Atlanta, GA",
    org_id: str = ORG_ID,
):
    return LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=CUSTOMER_ID,
        driver_id=driver_id,
        broker_id=broker_id,
        load_number=load_number,
        invoice_number=f"INV-{load_number}",
        gross_amount=Decimal("1500.00"),
        pickup_date=pickup_date,
        delivery_date=delivery_date,
        pickup_location=pickup_location,
        delivery_location=delivery_location,
    )


def _payment(
    db_session,
    *,
    load_id: str,
    expected: str,
    received: str,
    status: LoadPaymentStatus,
    factoring_used: bool = False,
    factoring_status: FactoringWorkflowStatus = FactoringWorkflowStatus.NOT_FACTORED,
    reconciliation_status: FactoringReconciliationStatus = FactoringReconciliationStatus.UNRECONCILED,
    reserve_amount: str = "0",
):
    record = PaymentReconciliationService(db_session).get_or_create_for_load(str(load_id), ORG_ID)
    record.expected_amount = Decimal(expected)
    record.amount_received = Decimal(received)
    record.payment_status = status
    record.factoring_used = factoring_used
    record.factoring_status = factoring_status
    record.reconciliation_status = reconciliation_status
    record.reserve_amount = Decimal(reserve_amount)
    record.reserve_paid_amount = Decimal("0")
    record.paid_date = datetime.now(timezone.utc) if status == LoadPaymentStatus.PAID else None
    return record


def test_operational_analytics_calculates_revenue_unpaid_aging_and_collections(db_session):
    _seed_parties(db_session)
    today = datetime.now(timezone.utc).date()
    paid_load = _make_load(db_session, load_number="PAID", delivery_date=today - timedelta(days=5))
    partial_load = _make_load(db_session, load_number="PART", delivery_date=today - timedelta(days=20))
    old_load = _make_load(db_session, load_number="OLD", delivery_date=today - timedelta(days=75), broker_id=BROKER_2_ID, driver_id=DRIVER_2_ID, pickup_location="Chicago, IL", delivery_location="Memphis, TN")

    _payment(db_session, load_id=paid_load.id, expected="1000", received="1000", status=LoadPaymentStatus.PAID, reconciliation_status=FactoringReconciliationStatus.RECONCILED)
    _payment(db_session, load_id=partial_load.id, expected="2000", received="500", status=LoadPaymentStatus.PARTIALLY_PAID, factoring_used=True, factoring_status=FactoringWorkflowStatus.FUNDED, reserve_amount="300")
    _payment(db_session, load_id=old_load.id, expected="3000", received="0", status=LoadPaymentStatus.DISPUTED)

    data = OperationalAnalyticsService(db_session).get_operational_analytics(org_id=ORG_ID)

    assert data["revenue"]["total_revenue"] == "6000.00"
    assert data["revenue"]["paid_revenue"] == "1000.00"
    assert data["revenue"]["unpaid_revenue"] == "4500.00"
    assert data["revenue"]["factored_revenue"] == "2000.00"
    assert data["revenue"]["invoice_count"] == 3
    assert data["unpaid_invoices"]["unpaid_count"] == 2
    assert data["unpaid_invoices"]["partially_paid_count"] == 1
    assert data["collections"]["reserve_pending_total"] == "300.00"
    assert data["collections"]["dispute_count"] == 1
    assert data["collections"]["risk_summary"]["high_risk_count"] == 1
    bucket_60 = next(bucket for bucket in data["aging_report"]["buckets"] if bucket["bucket"] == "60_plus")
    assert bucket_60["count"] == 1
    assert bucket_60["balance"] == "3000.00"


def test_operational_analytics_groups_brokers_drivers_lanes_and_filters(db_session):
    _seed_parties(db_session)
    today = datetime.now(timezone.utc).date()
    load_a = _make_load(db_session, load_number="A", delivery_date=today - timedelta(days=10))
    load_b = _make_load(db_session, load_number="B", delivery_date=today - timedelta(days=40), broker_id=BROKER_2_ID, driver_id=DRIVER_2_ID, pickup_location="Miami, FL", delivery_location="Nashville, TN")
    _payment(db_session, load_id=load_a.id, expected="1200", received="1200", status=LoadPaymentStatus.PAID, reconciliation_status=FactoringReconciliationStatus.RECONCILED)
    _payment(db_session, load_id=load_b.id, expected="1800", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT, factoring_used=True, factoring_status=FactoringWorkflowStatus.SUBMITTED_TO_FACTORING)

    filtered = OperationalAnalyticsService(db_session).get_operational_analytics(org_id=ORG_ID, broker_id=BROKER_2_ID)

    assert filtered["revenue"]["total_revenue"] == "1800.00"
    assert filtered["broker_performance"][0]["name"] == "Fast Broker"
    assert filtered["driver_profitability"][0]["name"] == "Ben Driver"
    assert filtered["lane_profitability"][0]["name"] == "Miami, FL → Nashville, TN"
    assert filtered["filter_options"]["brokers"] == [
        {"id": BROKER_2_ID, "name": "Fast Broker"},
        {"id": BROKER_ID, "name": "Prime Broker"},
    ]


def test_operational_analytics_excludes_other_org_and_honors_date_range(db_session):
    _seed_parties(db_session)
    today = datetime.now(timezone.utc).date()
    in_range = _make_load(db_session, load_number="IN", delivery_date=today - timedelta(days=5))
    out_range = _make_load(db_session, load_number="OUT", delivery_date=today - timedelta(days=100))
    other = _make_load(db_session, load_number="OTHER", delivery_date=today - timedelta(days=5), org_id=OTHER_ORG_ID)
    _payment(db_session, load_id=in_range.id, expected="100", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)
    _payment(db_session, load_id=out_range.id, expected="900", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)
    record = PaymentReconciliationService(db_session).get_or_create_for_load(str(other.id), OTHER_ORG_ID)
    record.expected_amount = Decimal("999")
    record.amount_received = Decimal("0")
    record.payment_status = LoadPaymentStatus.AWAITING_PAYMENT

    data = OperationalAnalyticsService(db_session).get_operational_analytics(org_id=ORG_ID, date_from=today - timedelta(days=30), date_to=today)

    assert data["revenue"]["total_revenue"] == "100.00"
    assert data["revenue"]["invoice_count"] == 1


def test_driver_blocked_from_operational_analytics_authorizer():
    with pytest.raises(ForbiddenError):
        _authorize_reports_read({"role": "driver"})
