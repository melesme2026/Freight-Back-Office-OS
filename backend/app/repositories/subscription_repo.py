from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.subscription_status import SubscriptionStatus
from app.domain.models.subscription import Subscription


class SubscriptionRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def get_by_id(
        self,
        subscription_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> Subscription | None:
        normalized_subscription_id = self._normalize_uuid(
            subscription_id,
            field_name="subscription_id",
        )

        stmt = select(Subscription).where(Subscription.id == normalized_subscription_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        service_plan_id: uuid.UUID | str | None = None,
        status: SubscriptionStatus | str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[Subscription], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_customer_account_id = (
            self._normalize_uuid(customer_account_id, field_name="customer_account_id")
            if customer_account_id is not None
            else None
        )
        normalized_service_plan_id = (
            self._normalize_uuid(service_plan_id, field_name="service_plan_id")
            if service_plan_id is not None
            else None
        )
        normalized_status = self._normalize_status(status)

        stmt = select(Subscription)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Subscription)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(Subscription.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(
                Subscription.organization_id == normalized_organization_id
            )

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Subscription.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                Subscription.customer_account_id == normalized_customer_account_id
            )

        if normalized_service_plan_id is not None:
            stmt = stmt.where(Subscription.service_plan_id == normalized_service_plan_id)
            count_stmt = count_stmt.where(
                Subscription.service_plan_id == normalized_service_plan_id
            )

        if normalized_status is not None:
            stmt = stmt.where(Subscription.status == normalized_status)
            count_stmt = count_stmt.where(Subscription.status == normalized_status)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Subscription.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def delete(self, subscription: Subscription) -> None:
        self.db.delete(subscription)
        self.db.flush()

    def _apply_related(
        self,
        stmt: Select[tuple[Subscription]],
    ) -> Select[tuple[Subscription]]:
        return stmt.options(
            selectinload(Subscription.customer_account),
            selectinload(Subscription.service_plan),
            selectinload(Subscription.billing_invoices),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    def _normalize_status(
        self,
        value: SubscriptionStatus | str | None,
    ) -> SubscriptionStatus | None:
        if value is None:
            return None

        if isinstance(value, SubscriptionStatus):
            return value

        normalized = str(value).strip().lower()

        for status in SubscriptionStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValueError(f"Invalid status: {value}")