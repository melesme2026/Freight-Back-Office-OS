from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.channel import Channel
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.notification import Notification


class NotificationRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)
        return notification

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        return self.db.scalar(stmt)

    def get_by_provider_message_id(
        self,
        provider_message_id: str,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.provider_message_id == provider_message_id
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        driver_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        channel: Channel | None = None,
        status: NotificationStatus | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Notification], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(Notification)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Notification)

        if organization_id is not None:
            stmt = stmt.where(Notification.organization_id == organization_id)
            count_stmt = count_stmt.where(Notification.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Notification.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                Notification.customer_account_id == customer_account_id
            )

        if driver_id is not None:
            stmt = stmt.where(Notification.driver_id == driver_id)
            count_stmt = count_stmt.where(Notification.driver_id == driver_id)

        if load_id is not None:
            stmt = stmt.where(Notification.load_id == load_id)
            count_stmt = count_stmt.where(Notification.load_id == load_id)

        if channel is not None:
            stmt = stmt.where(Notification.channel == channel)
            count_stmt = count_stmt.where(Notification.channel == channel)

        if status is not None:
            stmt = stmt.where(Notification.status == status)
            count_stmt = count_stmt.where(Notification.status == status)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)
        return notification

    def delete(self, notification: Notification) -> None:
        self.db.delete(notification)
        self.db.flush()