from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
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
        status: str | NotificationStatus = NotificationStatus.QUEUED,
    ) -> Notification:
        notification = Notification(
            organization_id=self._require_text(organization_id, field_name="organization_id"),
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            load_id=self._clean_text(load_id),
            created_by_staff_user_id=self._clean_text(created_by_staff_user_id),
            channel=self._require_text(channel, field_name="channel"),
            direction=self._require_text(direction, field_name="direction"),
            message_type=self._require_text(message_type, field_name="message_type"),
            subject=self._clean_text(subject),
            body_text=self._clean_text(body_text),
            provider_message_id=self._clean_text(provider_message_id),
            status=self._normalize_status(status),
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            error_message=None,
        )
        created = self.notification_repo.create(notification)
        return (
            self.notification_repo.get_by_id(
                created.id,
                organization_id=organization_id,
            )
            or created
        )

    def get_notification(self, notification_id: str, *, organization_id: str) -> Notification:
        normalized_notification_id = self._require_text(
            notification_id,
            field_name="notification_id",
        )
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        notification = self.notification_repo.get_by_id(
            normalized_notification_id,
            organization_id=normalized_organization_id,
        )
        if notification is None:
            raise NotFoundError(
                "Notification not found",
                details={"notification_id": normalized_notification_id},
            )
        if str(notification.organization_id) != normalized_organization_id:
            raise UnauthorizedError("Notification is not in authenticated organization")
        return notification

    def list_notifications(
        self,
        *,
        organization_id: str,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        channel: str | None = None,
        status: str | NotificationStatus | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Notification], int]:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        return self.notification_repo.list(
            organization_id=normalized_organization_id,
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            load_id=self._clean_text(load_id),
            channel=self._clean_text(channel),
            status=self._normalize_status(status, allow_none=True),
            page=page,
            page_size=page_size,
        )

    def mark_sent(
        self,
        *,
        notification_id: str,
        organization_id: str,
        provider_message_id: str | None = None,
    ) -> Notification:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        notification = self.get_notification(
            notification_id,
            organization_id=normalized_organization_id,
        )
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        if provider_message_id:
            notification.provider_message_id = self._clean_text(provider_message_id)
        notification.error_message = None
        updated = self.notification_repo.update(notification)
        return (
            self.notification_repo.get_by_id(
                updated.id,
                organization_id=normalized_organization_id,
            )
            or updated
        )

    def mark_delivered(self, *, notification_id: str, organization_id: str) -> Notification:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        notification = self.get_notification(
            notification_id,
            organization_id=normalized_organization_id,
        )
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.now(timezone.utc)
        notification.error_message = None
        updated = self.notification_repo.update(notification)
        return (
            self.notification_repo.get_by_id(
                updated.id,
                organization_id=normalized_organization_id,
            )
            or updated
        )

    def mark_failed(
        self,
        *,
        notification_id: str,
        organization_id: str,
        error_message: str | None = None,
    ) -> Notification:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        notification = self.get_notification(
            notification_id,
            organization_id=normalized_organization_id,
        )
        notification.status = NotificationStatus.FAILED
        notification.failed_at = datetime.now(timezone.utc)
        notification.error_message = self._clean_text(error_message)
        updated = self.notification_repo.update(notification)
        return (
            self.notification_repo.get_by_id(
                updated.id,
                organization_id=normalized_organization_id,
            )
            or updated
        )

    def _normalize_status(
        self,
        value: str | NotificationStatus | None,
        *,
        allow_none: bool = False,
    ) -> NotificationStatus | None:
        if value is None:
            if allow_none:
                return None
            return NotificationStatus.QUEUED

        if isinstance(value, NotificationStatus):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, NotificationStatus] = {
            "queued": NotificationStatus.QUEUED,
            "pending": NotificationStatus.QUEUED,
            "sent": NotificationStatus.SENT,
            "delivered": NotificationStatus.DELIVERED,
            "failed": NotificationStatus.FAILED,
            "error": NotificationStatus.FAILED,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid notification status",
            details={"status": value},
        )

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned
