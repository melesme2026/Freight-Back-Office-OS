from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.billing_cycle import BillingCycle
from app.domain.enums.subscription_status import SubscriptionStatus
from app.domain.models.subscription import Subscription
from app.repositories.service_plan_repo import ServicePlanRepository
from app.repositories.subscription_repo import SubscriptionRepository


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.service_plan_repo = ServicePlanRepository(db)

    def create_subscription(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        service_plan_id: str,
        starts_at,
        billing_email: str | None = None,
        notes: str | None = None,
    ) -> Subscription:
        service_plan = self.service_plan_repo.get_by_id(service_plan_id)
        if service_plan is None:
            raise NotFoundError(
                "Service plan not found",
                details={"service_plan_id": service_plan_id},
            )

        period_end = self._calculate_period_end(
            starts_at=starts_at,
            billing_cycle=str(service_plan.billing_cycle),
        )

        normalized_billing_email = billing_email.strip().lower() if billing_email else None

        subscription = Subscription(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            service_plan_id=service_plan_id,
            status=SubscriptionStatus.ACTIVE,
            starts_at=starts_at,
            ends_at=None,
            current_period_start=starts_at,
            current_period_end=period_end,
            cancel_at_period_end=False,
            cancelled_at=None,
            billing_email=normalized_billing_email,
            notes=notes,
        )
        return self.subscription_repo.create(subscription)

    def get_subscription(self, subscription_id: str) -> Subscription:
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            raise NotFoundError(
                "Subscription not found",
                details={"subscription_id": subscription_id},
            )
        return subscription

    def list_subscriptions(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        service_plan_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Subscription], int]:
        return self.subscription_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            service_plan_id=service_plan_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def update_subscription(
        self,
        *,
        subscription_id: str,
        **updates: Any,
    ) -> Subscription:
        subscription = self.get_subscription(subscription_id)

        for field, value in updates.items():
            if not hasattr(subscription, field) or value is None:
                continue

            if field == "billing_email" and isinstance(value, str):
                value = value.strip().lower()

            setattr(subscription, field, value)

        return self.subscription_repo.update(subscription)

    def cancel_subscription(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> Subscription:
        subscription = self.get_subscription(subscription_id)
        subscription.cancel_at_period_end = cancel_at_period_end

        if cancel_at_period_end:
            return self.subscription_repo.update(subscription)

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = subscription.current_period_start
        subscription.ends_at = subscription.current_period_start

        return self.subscription_repo.update(subscription)

    def _calculate_period_end(self, *, starts_at, billing_cycle: str):
        cycle = BillingCycle(billing_cycle)

        if cycle == BillingCycle.WEEKLY:
            return starts_at + timedelta(days=7)

        if cycle == BillingCycle.MONTHLY:
            return starts_at + timedelta(days=30)

        if cycle == BillingCycle.QUARTERLY:
            return starts_at + timedelta(days=90)

        if cycle == BillingCycle.ANNUAL:
            return starts_at + timedelta(days=365)

        return starts_at + timedelta(days=30)