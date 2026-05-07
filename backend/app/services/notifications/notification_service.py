from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
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
        organization_id: str | None,
        channel: str,
        direction: str,
        message_type: str,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_id: str | None = None,
        broker_id: str | None = None,
        demo_request_id: str | None = None,
        created_by_staff_user_id: str | None = None,
        recipient: str | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        provider_message_id: str | None = None,
        status: str | NotificationStatus = NotificationStatus.QUEUED,
    ) -> Notification:
        notification = Notification(
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            load_id=self._clean_text(load_id),
            document_id=self._clean_text(document_id),
            broker_id=self._clean_text(broker_id),
            demo_request_id=self._clean_text(demo_request_id),
            created_by_staff_user_id=self._clean_text(created_by_staff_user_id),
            channel=self._require_text(channel, field_name="channel"),
            direction=self._require_text(direction, field_name="direction"),
            message_type=self._require_text(message_type, field_name="message_type"),
            subject=self._clean_text(subject),
            body_text=self._clean_text(body_text),
            recipient=self._clean_text(recipient),
            provider_message_id=self._clean_text(provider_message_id),
            status=self._normalize_status(status),
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            error_message=None,
        )
        created = self.notification_repo.create(notification)
        if organization_id is None:
            return created
        return (
            self.notification_repo.get_by_id(
                created.id,
                organization_id=organization_id,
            )
            or created
        )

    def find_existing_notification(
        self,
        *,
        message_type: str,
        channel: str,
        organization_id: str | None = None,
        recipient: str | None = None,
        load_id: str | None = None,
        document_id: str | None = None,
        driver_id: str | None = None,
        demo_request_id: str | None = None,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.message_type == self._require_text(message_type, field_name="message_type"),
            Notification.channel == self._require_text(channel, field_name="channel"),
        )
        if self._clean_text(organization_id) is None:
            stmt = stmt.where(Notification.organization_id.is_(None))
        else:
            stmt = stmt.where(Notification.organization_id == self._clean_text(organization_id))
        filters = {
            Notification.recipient: recipient,
            Notification.load_id: load_id,
            Notification.document_id: document_id,
            Notification.driver_id: driver_id,
            Notification.demo_request_id: demo_request_id,
        }
        for column, value in filters.items():
            cleaned = self._clean_text(value)
            if cleaned is not None:
                stmt = stmt.where(column == cleaned)
        return self.db.scalar(stmt.order_by(Notification.created_at.desc()).limit(1))

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
        organization_id: str | None,
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
        organization_id: str | None,
        provider_message_id: str | None = None,
    ) -> Notification:
        normalized_organization_id = self._clean_text(organization_id)
        notification = (
            self.get_notification(notification_id, organization_id=normalized_organization_id)
            if normalized_organization_id is not None
            else self.db.get(Notification, notification_id)
        )
        if notification is None:
            raise NotFoundError("Notification not found", details={"notification_id": notification_id})
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        if provider_message_id:
            notification.provider_message_id = self._clean_text(provider_message_id)
        notification.error_message = None
        updated = self.notification_repo.update(notification)
        if normalized_organization_id is None:
            return updated
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
        organization_id: str | None,
        error_message: str | None = None,
    ) -> Notification:
        normalized_organization_id = self._clean_text(organization_id)
        notification = (
            self.get_notification(notification_id, organization_id=normalized_organization_id)
            if normalized_organization_id is not None
            else self.db.get(Notification, notification_id)
        )
        if notification is None:
            raise NotFoundError("Notification not found", details={"notification_id": notification_id})
        notification.status = NotificationStatus.FAILED
        notification.failed_at = datetime.now(timezone.utc)
        notification.error_message = self._clean_text(error_message)
        updated = self.notification_repo.update(notification)
        if normalized_organization_id is None:
            return updated
        return (
            self.notification_repo.get_by_id(
                updated.id,
                organization_id=normalized_organization_id,
            )
            or updated
        )

    def mark_skipped(
        self,
        *,
        notification_id: str,
        organization_id: str | None,
        error_message: str | None = None,
    ) -> Notification:
        notification = (
            self.get_notification(notification_id, organization_id=organization_id)
            if organization_id is not None
            else self.db.get(Notification, notification_id)
        )
        if notification is None:
            raise NotFoundError(
                "Notification not found",
                details={"notification_id": notification_id},
            )
        notification.status = NotificationStatus.SKIPPED
        notification.failed_at = datetime.now(timezone.utc)
        notification.error_message = self._clean_text(error_message)
        updated = self.notification_repo.update(notification)
        return updated

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
            "skipped": NotificationStatus.SKIPPED,
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
