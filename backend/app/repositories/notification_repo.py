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

    def get_by_id(self, notification_id: uuid.UUID | str) -> Notification | None:
        normalized_notification_id = self._normalize_uuid(
            notification_id,
            field_name="notification_id",
        )
        stmt = select(Notification).where(Notification.id == normalized_notification_id)
        return self.db.scalar(stmt)

    def get_by_provider_message_id(
        self,
        provider_message_id: str,
    ) -> Notification | None:
        normalized_provider_message_id = self._normalize_required_text(
            provider_message_id,
            field_name="provider_message_id",
        )
        stmt = select(Notification).where(
            Notification.provider_message_id == normalized_provider_message_id
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        driver_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        channel: Channel | str | None = None,
        status: NotificationStatus | str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Notification], int]:
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
        normalized_driver_id = (
            self._normalize_uuid(driver_id, field_name="driver_id")
            if driver_id is not None
            else None
        )
        normalized_load_id = (
            self._normalize_uuid(load_id, field_name="load_id")
            if load_id is not None
            else None
        )
        normalized_channel = self._normalize_channel(channel)
        normalized_status = self._normalize_status(status)

        stmt = select(Notification)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Notification)

        if normalized_organization_id is not None:
            stmt = stmt.where(Notification.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(Notification.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Notification.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                Notification.customer_account_id == normalized_customer_account_id
            )

        if normalized_driver_id is not None:
            stmt = stmt.where(Notification.driver_id == normalized_driver_id)
            count_stmt = count_stmt.where(Notification.driver_id == normalized_driver_id)

        if normalized_load_id is not None:
            stmt = stmt.where(Notification.load_id == normalized_load_id)
            count_stmt = count_stmt.where(Notification.load_id == normalized_load_id)

        if normalized_channel is not None:
            stmt = stmt.where(Notification.channel == normalized_channel)
            count_stmt = count_stmt.where(Notification.channel == normalized_channel)

        if normalized_status is not None:
            stmt = stmt.where(Notification.status == normalized_status)
            count_stmt = count_stmt.where(Notification.status == normalized_status)

        total = int(self.db.scalar(count_stmt) or 0)

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

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _normalize_required_text(value: str, *, field_name: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")
        return normalized

    def _normalize_channel(self, value: Channel | str | None) -> Channel | None:
        if value is None:
            return None

        if isinstance(value, Channel):
            return value

        normalized = str(value).strip().lower()

        for channel in Channel:
            if normalized == channel.value.lower():
                return channel
            if normalized == channel.name.lower():
                return channel

        raise ValueError(f"Invalid channel: {value}")

    def _normalize_status(
        self,
        value: NotificationStatus | str | None,
    ) -> NotificationStatus | None:
        if value is None:
            return None

        if isinstance(value, NotificationStatus):
            return value

        normalized = str(value).strip().lower()

        for status in NotificationStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValueError(f"Invalid status: {value}")