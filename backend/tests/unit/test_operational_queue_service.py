from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.domain.enums.load_status import LoadStatus
from app.services.loads.operational_queue_service import OperationalQueueService


def _load(**overrides):
    base = {
        "status": LoadStatus.BOOKED,
        "has_ratecon": False,
        "has_bol": False,
        "has_invoice": False,
        "documents": [],
        "updated_at": datetime.now(timezone.utc),
        "submitted_at": None,
        "funded_at": None,
        "paid_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_queue_missing_documents_and_upload_pod_next_action() -> None:
    service = OperationalQueueService()
    load = _load(status=LoadStatus.DELIVERED, has_ratecon=True, has_bol=False, has_invoice=False)

    result = service.evaluate_load(load)

    assert result["queue"] == "missing_documents"
    assert result["next_action"]["code"] == "upload_pod"


def test_queue_ready_to_submit_and_submit_to_broker_action() -> None:
    service = OperationalQueueService()
    load = _load(
        status=LoadStatus.INVOICE_READY,
        has_ratecon=True,
        has_bol=True,
        has_invoice=True,
    )

    result = service.evaluate_load(load)

    assert result["queue"] == "ready_to_submit"
    assert result["next_action"]["code"] == "submit_to_broker"


def test_overdue_submitted_load_is_payment_overdue_and_follow_up() -> None:
    service = OperationalQueueService()
    now = datetime(2026, 4, 20, tzinfo=timezone.utc)
    load = _load(
        status=LoadStatus.SUBMITTED_TO_BROKER,
        has_ratecon=True,
        has_bol=True,
        has_invoice=True,
        submitted_at=now - timedelta(days=5),
    )

    result = service.evaluate_load(load, now=now)

    assert result["queue"] == "payment_overdue"
    assert result["is_overdue"] is True
    assert result["days_in_state"] == 5
    assert result["next_action"]["code"] == "follow_up_broker"


def test_disputed_priority_queue_and_action() -> None:
    service = OperationalQueueService()
    load = _load(status=LoadStatus.DISPUTED)

    result = service.evaluate_load(load)

    assert result["queue"] == "disputed_or_short_paid"
    assert result["next_action"]["code"] == "resolve_dispute"
