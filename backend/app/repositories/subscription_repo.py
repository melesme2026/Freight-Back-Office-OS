from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.subscription_status import SubscriptionStatus
from app.domain.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)
        return subscription

    def get_by_id(self, subscription_id: uuid.UUID) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        service_plan_id: uuid.UUID | None = None,
        status: SubscriptionStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Subscription], int]:
        stmt = select(Subscription)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Subscription)

        if organization_id is not None:
            stmt = stmt.where(Subscription.organization_id == organization_id)
            count_stmt = count_stmt.where(Subscription.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Subscription.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                Subscription.customer_account_id == customer_account_id
            )

        if service_plan_id is not None:
            stmt = stmt.where(Subscription.service_plan_id == service_plan_id)
            count_stmt = count_stmt.where(
                Subscription.service_plan_id == service_plan_id
            )

        if status is not None:
            stmt = stmt.where(Subscription.status == status)
            count_stmt = count_stmt.where(Subscription.status == status)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(Subscription.created_at.desc()).offset(offset).limit(page_size)

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