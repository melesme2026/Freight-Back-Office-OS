from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.notification_repo = NotificationRepository(db)

    def create_notification(
        self,
        *,
        organization_id: str,
        channel: str,
        direction: str,
        message_type: str,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        created_by_staff_user_id: str | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        provider_message_id: str | None = None,
        status: str = NotificationStatus.QUEUED,
    ) -> Notification:
        notification = Notification(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            created_by_staff_user_id=created_by_staff_user_id,
            channel=channel,
            direction=direction,
            message_type=message_type,
            subject=subject,
            body_text=body_text,
            provider_message_id=provider_message_id,
            status=status,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            error_message=None,
        )
        return self.notification_repo.create(notification)

    def get_notification(self, notification_id: str) -> Notification:
        notification = self.notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotFoundError(
                "Notification not found",
                details={"notification_id": notification_id},
            )
        return notification

    def list_notifications(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        channel: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Notification], int]:
        return self.notification_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            channel=channel,
            status=status,
            page=page,
            page_size=page_size,
        )

    def mark_sent(
        self,
        *,
        notification_id: str,
        provider_message_id: str | None = None,
    ) -> Notification:
        notification = self.get_notification(notification_id)
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        if provider_message_id:
            notification.provider_message_id = provider_message_id
        return self.notification_repo.update(notification)

    def mark_delivered(self, *, notification_id: str) -> Notification:
        notification = self.get_notification(notification_id)
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.now(timezone.utc)
        return self.notification_repo.update(notification)

    def mark_failed(
        self,
        *,
        notification_id: str,
        error_message: str | None = None,
    ) -> Notification:
        notification = self.get_notification(notification_id)
        notification.status = NotificationStatus.FAILED
        notification.failed_at = datetime.now(timezone.utc)
        notification.error_message = error_message
        return self.notification_repo.update(notification)