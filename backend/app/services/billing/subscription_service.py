from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
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
        starts_at: Any,
        billing_email: str | None = None,
        notes: str | None = None,
    ) -> Subscription:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        normalized_customer_account_id = self._require_text(
            customer_account_id,
            field_name="customer_account_id",
        )
        normalized_service_plan_id = self._require_text(
            service_plan_id,
            field_name="service_plan_id",
        )
        normalized_starts_at = self._normalize_datetime(
            starts_at,
            field_name="starts_at",
        )

        service_plan = self.service_plan_repo.get_by_id(normalized_service_plan_id)
        if service_plan is None:
            raise NotFoundError(
                "Service plan not found",
                details={"service_plan_id": normalized_service_plan_id},
            )

        period_end = self._calculate_period_end(
            starts_at=normalized_starts_at,
            billing_cycle=getattr(service_plan.billing_cycle, "value", str(service_plan.billing_cycle)),
        )

        subscription = Subscription(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
            service_plan_id=normalized_service_plan_id,
            status=SubscriptionStatus.ACTIVE,
            starts_at=normalized_starts_at,
            ends_at=None,
            current_period_start=normalized_starts_at,
            current_period_end=period_end,
            cancel_at_period_end=False,
            cancelled_at=None,
            billing_email=self._normalize_email(billing_email),
            notes=self._clean_text(notes),
        )
        created = self.subscription_repo.create(subscription)
        return self.subscription_repo.get_by_id(created.id, include_related=True) or created

    def get_subscription(self, subscription_id: str) -> Subscription:
        subscription = self.subscription_repo.get_by_id(
            subscription_id,
            include_related=True,
        )
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
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
            service_plan_id=self._clean_text(service_plan_id),
            status=self._normalize_status(status, allow_none=True),
            page=page,
            page_size=page_size,
            include_related=True,
        )

    def update_subscription(
        self,
        *,
        subscription_id: str,
        **updates: Any,
    ) -> Subscription:
        subscription = self.get_subscription(subscription_id)

        for field, value in updates.items():
            if not hasattr(subscription, field):
                continue

            if field == "status":
                if value is None:
                    continue
                setattr(subscription, field, self._normalize_status(value))
                continue

            if field in {
                "starts_at",
                "ends_at",
                "current_period_start",
                "current_period_end",
                "cancelled_at",
            }:
                setattr(
                    subscription,
                    field,
                    self._normalize_datetime(value, field_name=field, allow_none=True),
                )
                continue

            if field == "billing_email":
                setattr(subscription, field, self._normalize_email(value))
                continue

            if field == "notes":
                setattr(subscription, field, self._clean_text(value))
                continue

            if field == "cancel_at_period_end":
                if value is not None:
                    setattr(subscription, field, bool(value))
                continue

            if value is not None:
                setattr(subscription, field, value)

        updated = self.subscription_repo.update(subscription)
        return self.subscription_repo.get_by_id(updated.id, include_related=True) or updated

    def cancel_subscription(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> Subscription:
        subscription = self.get_subscription(subscription_id)
        subscription.cancel_at_period_end = cancel_at_period_end

        if cancel_at_period_end:
            updated = self.subscription_repo.update(subscription)
            return self.subscription_repo.get_by_id(updated.id, include_related=True) or updated

        now = datetime.utcnow()
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = now
        subscription.ends_at = now
        subscription.current_period_end = now

        updated = self.subscription_repo.update(subscription)
        return self.subscription_repo.get_by_id(updated.id, include_related=True) or updated

    def _calculate_period_end(self, *, starts_at: datetime, billing_cycle: str) -> datetime:
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

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _require_text(self, value: Any, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned

    @staticmethod
    def _normalize_email(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @staticmethod
    def _normalize_datetime(
        value: Any,
        *,
        field_name: str,
        allow_none: bool = False,
    ) -> datetime | None:
        if value is None or value == "":
            if allow_none:
                return None
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        try:
            return datetime.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _normalize_status(
        value: str | SubscriptionStatus | None,
        *,
        allow_none: bool = False,
    ) -> SubscriptionStatus | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                "status is required",
                details={"status": value},
            )

        if isinstance(value, SubscriptionStatus):
            return value

        normalized = str(value).strip().lower()
        if not normalized:
            if allow_none:
                return None
            raise ValidationError(
                "status is required",
                details={"status": value},
            )

        for status in SubscriptionStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValidationError(
            "Invalid subscription status",
            details={"status": value},
        )