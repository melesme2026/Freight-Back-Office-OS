from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums.billing_cycle import BillingCycle
from app.domain.models.service_plan import ServicePlan
from app.services.billing.subscription_service import SubscriptionService


def test_subscription_flow_create_and_cancel(db_session) -> None:
    plan = ServicePlan(
        organization_id="00000000-0000-0000-0000-000000000701",
        name="Starter Plan",
        code="starter",
        description="Starter monthly plan",
        billing_cycle=BillingCycle.MONTHLY,
        base_price="99.00",
        currency_code="USD",
        per_load_price="5.00",
        per_driver_price="2.00",
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    service = SubscriptionService(db_session)

    created = service.create_subscription(
        organization_id="00000000-0000-0000-0000-000000000701",
        customer_account_id="00000000-0000-0000-0000-000000000702",
        service_plan_id=str(plan.id),
        starts_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        billing_email="billing@test.com",
    )

    assert str(created.status) == "active"
    assert created.billing_email == "billing@test.com"

    cancelled = service.cancel_subscription(
        subscription_id=str(created.id),
        cancel_at_period_end=False,
    )

    assert str(cancelled.status) == "cancelled"
    assert cancelled.cancelled_at is not None