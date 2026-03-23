from __future__ import annotations

from datetime import datetime, timezone

from app.services.billing.subscription_service import SubscriptionService


def test_create_subscription_sets_active_defaults(db_session) -> None:
    service = SubscriptionService(db_session)

    item = service.create_subscription(
        organization_id="00000000-0000-0000-0000-000000000101",
        customer_account_id="00000000-0000-0000-0000-000000000102",
        service_plan_id="00000000-0000-0000-0000-000000000103",
        starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        billing_email="billing@example.com",
        notes="starter subscription",
    )

    assert str(item.status) == "active"
    assert str(item.customer_account_id) == "00000000-0000-0000-0000-000000000102"
    assert str(item.service_plan_id) == "00000000-0000-0000-0000-000000000103"
    assert item.cancel_at_period_end is False
    assert item.billing_email == "billing@example.com"


def test_update_subscription_changes_fields(db_session) -> None:
    service = SubscriptionService(db_session)

    item = service.create_subscription(
        organization_id="00000000-0000-0000-0000-000000000111",
        customer_account_id="00000000-0000-0000-0000-000000000112",
        service_plan_id="00000000-0000-0000-0000-000000000113",
        starts_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    updated = service.update_subscription(
        subscription_id=str(item.id),
        billing_email="updated@example.com",
        notes="updated notes",
        cancel_at_period_end=True,
    )

    assert updated.billing_email == "updated@example.com"
    assert updated.notes == "updated notes"
    assert updated.cancel_at_period_end is True


def test_cancel_subscription_at_period_end_sets_flag(db_session) -> None:
    service = SubscriptionService(db_session)

    item = service.create_subscription(
        organization_id="00000000-0000-0000-0000-000000000121",
        customer_account_id="00000000-0000-0000-0000-000000000122",
        service_plan_id="00000000-0000-0000-0000-000000000123",
        starts_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    updated = service.cancel_subscription(
        subscription_id=str(item.id),
        cancel_at_period_end=True,
    )

    assert updated.cancel_at_period_end is True


def test_cancel_subscription_immediate_marks_cancelled(db_session) -> None:
    service = SubscriptionService(db_session)

    item = service.create_subscription(
        organization_id="00000000-0000-0000-0000-000000000131",
        customer_account_id="00000000-0000-0000-0000-000000000132",
        service_plan_id="00000000-0000-0000-0000-000000000133",
        starts_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    updated = service.cancel_subscription(
        subscription_id=str(item.id),
        cancel_at_period_end=False,
    )

    assert str(updated.status) == "cancelled"
    assert updated.cancelled_at is not None
    assert updated.ends_at is not None