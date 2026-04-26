from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError
from app.domain.enums.follow_up_task import FollowUpTaskPriority, FollowUpTaskStatus, FollowUpTaskType
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.submission_packet import SubmissionPacket
from app.services.followups.follow_up_service import FollowUpService
from app.services.loads.load_service import LoadService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService

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


def _packet(db_session, *, load_id, org_id: str, sent_days_ago: int, accepted: bool = False):
    sent_at = datetime.now(timezone.utc) - timedelta(days=sent_days_ago)
    packet = SubmissionPacket(
        organization_id=org_id,
        load_id=load_id,
        packet_reference="PK-1",
        destination_type="broker",
        status="accepted" if accepted else "sent",
        sent_at=sent_at,
        accepted_at=(datetime.now(timezone.utc) if accepted else None),
    )
    db_session.add(packet)
    db_session.flush()
    return packet


def test_packet_sent_over_7_days_creates_follow_up(db_session):
    load = _make_load(db_session)
    _packet(db_session, load_id=load.id, org_id=ORG_ID, sent_days_ago=9)

    tasks = FollowUpService(db_session).generate_followups_for_load(str(load.id), ORG_ID)

    assert any(task.task_type == FollowUpTaskType.PACKET_FOLLOW_UP for task in tasks)


def test_packet_accepted_does_not_create_follow_up(db_session):
    load = _make_load(db_session)
    _packet(db_session, load_id=load.id, org_id=ORG_ID, sent_days_ago=10, accepted=True)

    tasks = FollowUpService(db_session).generate_followups_for_load(str(load.id), ORG_ID)

    assert all(task.task_type != FollowUpTaskType.PACKET_FOLLOW_UP for task in tasks)


def test_unpaid_over_30_days_creates_payment_overdue(db_session):
    load = _make_load(db_session)
    load.submitted_at = datetime.now(timezone.utc) - timedelta(days=35)
    payment = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), ORG_ID)
    payment.payment_status = LoadPaymentStatus.AWAITING_PAYMENT

    tasks = FollowUpService(db_session).generate_followups_for_load(str(load.id), ORG_ID)

    assert any(task.task_type == FollowUpTaskType.PAYMENT_OVERDUE for task in tasks)


def test_paid_cancels_payment_followups(db_session):
    load = _make_load(db_session)
    load.submitted_at = datetime.now(timezone.utc) - timedelta(days=35)
    payment_service = PaymentReconciliationService(db_session)
    payment = payment_service.get_or_create_for_load(str(load.id), ORG_ID)
    payment.payment_status = LoadPaymentStatus.AWAITING_PAYMENT
    service = FollowUpService(db_session)
    service.generate_followups_for_load(str(load.id), ORG_ID)

    payment.payment_status = LoadPaymentStatus.PAID
    service.generate_followups_for_load(str(load.id), ORG_ID)
    tasks = service.list_followups(ORG_ID, {"load_id": str(load.id)})

    assert any(task.task_type == FollowUpTaskType.PAYMENT_OVERDUE and task.status == FollowUpTaskStatus.CANCELED for task in tasks)


def test_reserve_pending_partial_short_disputed(db_session):
    load = _make_load(db_session)
    load.submitted_at = datetime.now(timezone.utc) - timedelta(days=5)
    payment = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), ORG_ID)
    service = FollowUpService(db_session)

    payment.payment_status = LoadPaymentStatus.RESERVE_PENDING
    tasks = service.generate_followups_for_load(str(load.id), ORG_ID)
    assert any(t.task_type == FollowUpTaskType.RESERVE_FOLLOW_UP for t in tasks)

    payment.payment_status = LoadPaymentStatus.PARTIALLY_PAID
    tasks = service.generate_followups_for_load(str(load.id), ORG_ID)
    assert any(t.task_type == FollowUpTaskType.PARTIAL_PAYMENT_FOLLOW_UP for t in tasks)

    payment.payment_status = LoadPaymentStatus.SHORT_PAID
    tasks = service.generate_followups_for_load(str(load.id), ORG_ID)
    short = next(t for t in tasks if t.task_type == FollowUpTaskType.SHORT_PAY_FOLLOW_UP)
    assert short.priority == FollowUpTaskPriority.URGENT

    payment.payment_status = LoadPaymentStatus.DISPUTED
    tasks = service.generate_followups_for_load(str(load.id), ORG_ID)
    dispute = next(t for t in tasks if t.task_type == FollowUpTaskType.DISPUTE_FOLLOW_UP)
    assert dispute.priority == FollowUpTaskPriority.URGENT


def test_duplicate_generation_does_not_duplicate_open_tasks(db_session):
    load = _make_load(db_session)
    load.submitted_at = datetime.now(timezone.utc) - timedelta(days=40)
    payment = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), ORG_ID)
    payment.payment_status = LoadPaymentStatus.AWAITING_PAYMENT
    service = FollowUpService(db_session)

    service.generate_followups_for_load(str(load.id), ORG_ID)
    service.generate_followups_for_load(str(load.id), ORG_ID)
    tasks = [t for t in service.list_followups(ORG_ID, {"load_id": str(load.id)}) if t.task_type == FollowUpTaskType.PAYMENT_OVERDUE]

    assert len(tasks) == 1


def test_complete_snooze_cancel_changes_status(db_session):
    load = _make_load(db_session)
    load.submitted_at = datetime.now(timezone.utc) - timedelta(days=40)
    payment = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), ORG_ID)
    payment.payment_status = LoadPaymentStatus.AWAITING_PAYMENT
    service = FollowUpService(db_session)
    task = service.generate_followups_for_load(str(load.id), ORG_ID)[0]

    snoozed = service.snooze_followup(str(task.id), ORG_ID, datetime.now(timezone.utc) + timedelta(days=1), None)
    assert snoozed.status == FollowUpTaskStatus.SNOOZED

    completed = service.complete_followup(str(task.id), ORG_ID, None)
    assert completed.status == FollowUpTaskStatus.COMPLETED

    canceled = service.cancel_followup(str(task.id), ORG_ID, None)
    assert canceled.status == FollowUpTaskStatus.CANCELED


def test_cross_org_access_denied(db_session):
    load = _make_load(db_session, organization_id=ORG_ID)
    with pytest.raises(NotFoundError):
        FollowUpService(db_session).generate_followups_for_load(str(load.id), OTHER_ORG_ID)
