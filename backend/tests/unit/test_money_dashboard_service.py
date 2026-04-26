from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.api.v1.reports import _authorize_reports_read
from app.core.exceptions import ForbiddenError
from app.domain.enums.follow_up_task import FollowUpTaskPriority, FollowUpTaskStatus, FollowUpTaskType
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.follow_up_task import FollowUpTask
from app.domain.models.submission_packet import SubmissionPacket
from app.services.loads.load_service import LoadService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService
from app.services.reports.money_dashboard_service import MoneyDashboardService


ORG_ID = "00000000-0000-0000-0000-000000008001"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000008002"


def _make_load(db_session, *, organization_id: str = ORG_ID, load_number: str = "LD-001"):
    return LoadService(db_session).create_load(
        organization_id=organization_id,
        customer_account_id="00000000-0000-0000-0000-000000009902",
        driver_id="00000000-0000-0000-0000-000000009903",
        load_number=load_number,
        gross_amount=Decimal("1500.00"),
        currency_code="USD",
    )


def _payment(db_session, *, load_id: str, org_id: str, expected: str, received: str, status: LoadPaymentStatus, factoring: bool = False, reserve: str = "0", advance: str = "0"):
    service = PaymentReconciliationService(db_session)
    record = service.get_or_create_for_load(str(load_id), org_id)
    record.expected_amount = Decimal(expected)
    record.amount_received = Decimal(received)
    record.payment_status = status
    record.factoring_used = factoring
    record.reserve_amount = Decimal(reserve)
    record.reserve_paid_amount = Decimal("0")
    record.advance_amount = Decimal(advance)
    record.paid_date = datetime.now(timezone.utc) if status == LoadPaymentStatus.PAID else None
    return record


def test_money_dashboard_summary_and_outstanding(db_session):
    load_paid = _make_load(db_session, load_number="LD-PAID")
    load_unpaid = _make_load(db_session, load_number="LD-UNPAID")

    _payment(db_session, load_id=load_paid.id, org_id=ORG_ID, expected="1000", received="1000", status=LoadPaymentStatus.PAID)
    _payment(db_session, load_id=load_unpaid.id, org_id=ORG_ID, expected="2000", received="500", status=LoadPaymentStatus.PARTIALLY_PAID)

    data = MoneyDashboardService(db_session).get_money_dashboard(ORG_ID)

    assert Decimal(str(data["summary"]["total_expected"])) == Decimal("3000")
    assert Decimal(str(data["summary"]["total_received"])) == Decimal("1500")
    assert Decimal(str(data["summary"]["total_outstanding"])) == Decimal("1500")
    assert data["summary"]["unpaid_count"] == 1
    assert Decimal(str(data["summary"]["paid_amount"])) == Decimal("1000")


def test_overdue_and_aging_buckets_use_submission_sent_at(db_session):
    load = _make_load(db_session, load_number="LD-OLD")
    _payment(db_session, load_id=load.id, org_id=ORG_ID, expected="1200", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)

    packet = SubmissionPacket(
        organization_id=ORG_ID,
        load_id=load.id,
        packet_reference="PK-OLD",
        destination_type="broker",
        status="sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=95),
    )
    db_session.add(packet)
    db_session.flush()

    data = MoneyDashboardService(db_session).get_money_dashboard(ORG_ID)
    assert data["summary"]["overdue_count"] == 1
    assert Decimal(str(data["summary"]["overdue_amount"])) == Decimal("1200")
    ninety_plus = next(item for item in data["aging_buckets"] if item["bucket"] == "90+")
    assert ninety_plus["count"] == 1


def test_factoring_direct_reserve_shortpay_disputed_and_attention(db_session):
    factoring_load = _make_load(db_session, load_number="LD-FCT")
    direct_load = _make_load(db_session, load_number="LD-DIR")
    disputed_load = _make_load(db_session, load_number="LD-DSP")

    _payment(
        db_session,
        load_id=factoring_load.id,
        org_id=ORG_ID,
        expected="2200",
        received="1200",
        status=LoadPaymentStatus.RESERVE_PENDING,
        factoring=True,
        reserve="500",
        advance="1200",
    )
    _payment(
        db_session,
        load_id=direct_load.id,
        org_id=ORG_ID,
        expected="800",
        received="500",
        status=LoadPaymentStatus.SHORT_PAID,
        factoring=False,
    )
    _payment(
        db_session,
        load_id=disputed_load.id,
        org_id=ORG_ID,
        expected="900",
        received="0",
        status=LoadPaymentStatus.DISPUTED,
        factoring=False,
    )

    due = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(
        FollowUpTask(
            organization_id=ORG_ID,
            load_id=direct_load.id,
            task_type=FollowUpTaskType.SHORT_PAY_FOLLOW_UP,
            status=FollowUpTaskStatus.OPEN,
            priority=FollowUpTaskPriority.URGENT,
            title="Short pay",
            due_at=due,
            recommended_action="Call broker",
        )
    )
    db_session.add(
        FollowUpTask(
            organization_id=ORG_ID,
            load_id=disputed_load.id,
            task_type=FollowUpTaskType.DISPUTE_FOLLOW_UP,
            status=FollowUpTaskStatus.COMPLETED,
            priority=FollowUpTaskPriority.HIGH,
            title="Dispute",
            due_at=due,
            recommended_action="Upload docs",
        )
    )
    db_session.flush()

    data = MoneyDashboardService(db_session).get_money_dashboard(ORG_ID)

    assert data["summary"]["short_paid_count"] == 1
    assert data["summary"]["disputed_count"] == 1
    assert Decimal(str(data["summary"]["reserve_pending_amount"])) == Decimal("500")

    factoring = data["factoring_vs_direct"]
    assert factoring["factored"]["count"] == 1
    assert Decimal(str(factoring["advance_total"])) == Decimal("1200")
    assert Decimal(str(factoring["direct_unpaid_total"])) == Decimal("1200")

    attention = data["needs_attention"]
    assert attention["urgent_count"] == 1
    assert attention["overdue_followups_count"] == 1
    assert len(attention["top_items"]) == 1


def test_cross_org_data_excluded(db_session):
    load_org = _make_load(db_session, organization_id=ORG_ID, load_number="LD-A")
    load_other = _make_load(db_session, organization_id=OTHER_ORG_ID, load_number="LD-B")

    _payment(db_session, load_id=load_org.id, org_id=ORG_ID, expected="100", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)
    _payment(db_session, load_id=load_other.id, org_id=OTHER_ORG_ID, expected="999", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)

    data = MoneyDashboardService(db_session).get_money_dashboard(ORG_ID)
    assert Decimal(str(data["summary"]["total_expected"])) == Decimal("100")


def test_driver_blocked_from_api_authorizer():
    with pytest.raises(ForbiddenError):
        _authorize_reports_read({"role": "driver"})
