from __future__ import annotations

import logging
from collections.abc import Iterable

from app.core.config import get_settings
from app.domain.enums.channel import Channel
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.driver import Driver
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.services.notifications.email_service import EmailService
from app.services.notifications.notification_service import NotificationService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OperationalNotificationService:
    """Email-first operational notifications that never block source actions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.notifications = NotificationService(db)
        self.email = EmailService()

    def document_uploaded(
        self,
        *,
        document: LoadDocument,
        driver: Driver | None = None,
        driver_confirmation: bool = False,
    ) -> None:
        load_label = self._load_label(document.load)
        document_label = self._document_label(document)
        ops_subject = f"Document uploaded: {document_label}"
        ops_body = "\n".join(
            [
                "A document was uploaded in Freight Back Office OS.",
                f"Document: {document_label}",
                f"Load: {load_label}",
                (
                    "Driver: "
                    f"{getattr(driver or document.driver, 'full_name', None) or 'Not assigned'}"
                ),
                f"Filename: {document.original_filename or 'Not provided'}",
            ]
        )
        self._create_and_deliver(
            organization_id=str(document.organization_id),
            event_type="document_uploaded",
            recipient=self._ops_recipient(),
            subject=ops_subject,
            body=ops_body,
            customer_account_id=self._str(document.customer_account_id),
            driver_id=self._str(document.driver_id),
            load_id=self._str(document.load_id),
            document_id=str(document.id),
            idempotency_fields={"document_id": str(document.id)},
        )

        effective_driver = driver or document.driver
        if driver_confirmation and effective_driver and self._clean(effective_driver.email):
            self._create_and_deliver(
                organization_id=str(document.organization_id),
                event_type="driver_upload_confirmation",
                recipient=str(effective_driver.email),
                subject="Document upload received",
                body="\n".join(
                    [
                        "We received your document upload.",
                        f"Document: {document_label}",
                        f"Load: {load_label}",
                        "No further action is needed unless your operations team contacts you.",
                    ]
                ),
                customer_account_id=self._str(document.customer_account_id),
                driver_id=str(effective_driver.id),
                load_id=self._str(document.load_id),
                document_id=str(document.id),
                idempotency_fields={
                    "document_id": str(document.id),
                    "driver_id": str(effective_driver.id),
                },
            )
        elif driver_confirmation:
            logger.info(
                "Driver upload confirmation skipped because driver email is unavailable",
                extra={"document_id": str(document.id), "driver_id": self._str(document.driver_id)},
            )

    def demo_request_received(
        self,
        *,
        demo_request_id: str,
        full_name: str,
        email: str,
        company: str,
        phone: str | None = None,
        fleet_size: str | None = None,
        message: str | None = None,
        status: str = "new",
        submitted_at: object | None = None,
    ) -> None:
        submitted_label = self._timestamp_label(submitted_at)
        lead_label = company or full_name
        ops_body = "\n".join(
            [
                "A new demo request was submitted to Freight Back Office OS.",
                f"Status: {status}",
                f"Submitted: {submitted_label}",
                f"Name: {full_name}",
                f"Company: {company}",
                f"Email: {email}",
                f"Phone: {phone or 'Not provided'}",
                f"Fleet size: {fleet_size or 'Not provided'}",
                f"Message: {message or 'Not provided'}",
            ]
        )
        self._create_and_deliver(
            organization_id=None,
            event_type="demo_request_received",
            recipient=self._ops_recipient(),
            subject=f"New Demo Request | {lead_label}",
            body=ops_body,
            demo_request_id=demo_request_id,
            idempotency_fields={"demo_request_id": demo_request_id},
        )

        acknowledgement_body = "\n".join(
            [
                f"Hi {full_name},",
                "",
                "Thank you for requesting a Freight Back Office OS demo.",
                "We received your request, and our team will review it and follow up with you.",
                "",
                "Freight Back Office OS",
            ]
        )
        self._create_and_deliver(
            organization_id=None,
            event_type="demo_request_acknowledgement",
            recipient=email,
            subject="We received your Freight Back Office OS demo request",
            body=acknowledgement_body,
            demo_request_id=demo_request_id,
            idempotency_fields={"demo_request_id": demo_request_id},
        )

    def missing_docs_reminder(self, *, load: Load, missing_documents: Iterable[str]) -> None:
        missing = [item.strip() for item in missing_documents if item and item.strip()]
        if not missing:
            return
        self._create_and_deliver(
            organization_id=str(load.organization_id),
            event_type="missing_docs_reminder",
            recipient=self._ops_recipient(),
            subject=f"Missing documents reminder: {self._load_label(load)}",
            body="\n".join(
                [
                    "This load is missing required documents.",
                    f"Load: {self._load_label(load)}",
                    "Missing documents:",
                    *[f"- {item}" for item in missing],
                ]
            ),
            customer_account_id=self._str(load.customer_account_id),
            driver_id=self._str(load.driver_id),
            load_id=str(load.id),
            broker_id=self._str(load.broker_id),
            idempotency_fields={"load_id": str(load.id)},
        )

    def invoice_submitted(self, *, load: Load) -> None:
        broker_name = getattr(load.broker, "name", None) or load.broker_name_raw or "Not provided"
        self._create_and_deliver(
            organization_id=str(load.organization_id),
            event_type="invoice_submitted",
            recipient=self._ops_recipient(),
            subject=f"Invoice submitted: {self._load_label(load)}",
            body="\n".join(
                [
                    "A load invoice was marked submitted.",
                    f"Load: {self._load_label(load)}",
                    f"Invoice: {load.invoice_number or 'Not provided'}",
                    f"Broker: {broker_name}",
                ]
            ),
            customer_account_id=self._str(load.customer_account_id),
            driver_id=self._str(load.driver_id),
            load_id=str(load.id),
            broker_id=self._str(load.broker_id),
            idempotency_fields={"load_id": str(load.id)},
        )

    def payment_status_updated(
        self, *, record: LoadPaymentRecord, previous_status: str | None = None
    ) -> None:
        status = getattr(record.payment_status, "value", str(record.payment_status))
        if previous_status == status:
            return
        event_type = (
            "payment_marked_paid"
            if status == LoadPaymentStatus.PAID.value
            else "payment_status_updated"
        )
        load = record.load
        subject = (
            f"Payment marked paid: {self._load_label(load)}"
            if event_type == "payment_marked_paid"
            else f"Payment status updated: {self._load_label(load)}"
        )
        self._create_and_deliver(
            organization_id=str(record.organization_id),
            event_type=event_type,
            recipient=self._ops_recipient(),
            subject=subject,
            body="\n".join(
                [
                    "A load payment status changed.",
                    f"Load: {self._load_label(load)}",
                    f"Previous status: {previous_status or 'Unknown'}",
                    f"Current status: {status}",
                    f"Amount received: {record.amount_received} {record.currency}",
                    f"Factoring used: {'Yes' if record.factoring_used else 'No'}",
                ]
            ),
            customer_account_id=self._str(load.customer_account_id),
            driver_id=self._str(load.driver_id),
            load_id=str(record.load_id),
            broker_id=self._str(load.broker_id),
            idempotency_fields={"load_id": str(record.load_id)},
        )

    def _create_and_deliver(
        self,
        *,
        organization_id: str | None,
        event_type: str,
        recipient: str | None,
        subject: str,
        body: str,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        document_id: str | None = None,
        broker_id: str | None = None,
        demo_request_id: str | None = None,
        idempotency_fields: dict[str, str] | None = None,
    ) -> None:
        try:
            recipient = self._clean(recipient)
            existing = self.notifications.find_existing_notification(
                organization_id=organization_id,
                channel=Channel.EMAIL.value,
                message_type=event_type,
                recipient=recipient,
                load_id=(idempotency_fields or {}).get("load_id"),
                document_id=(idempotency_fields or {}).get("document_id"),
                driver_id=(idempotency_fields or {}).get("driver_id"),
                demo_request_id=(idempotency_fields or {}).get("demo_request_id"),
            )
            if existing is not None:
                return

            initial_status = NotificationStatus.QUEUED
            reason = None
            if not self.settings.notifications_enabled:
                initial_status = NotificationStatus.SKIPPED
                reason = "Notifications are disabled."
            elif not recipient:
                initial_status = NotificationStatus.SKIPPED
                reason = "No notification recipient is configured."

            notification = self.notifications.create_notification(
                organization_id=organization_id,
                channel=Channel.EMAIL.value,
                direction="outbound",
                message_type=event_type,
                customer_account_id=customer_account_id,
                driver_id=driver_id,
                load_id=load_id,
                document_id=document_id,
                broker_id=broker_id,
                demo_request_id=demo_request_id,
                recipient=recipient,
                subject=subject,
                body_text=body,
                status=initial_status,
            )
            if reason:
                notification.error_message = reason
                self.notifications.notification_repo.update(notification)
                return

            if not self._email_configured():
                self.notifications.mark_skipped(
                    notification_id=str(notification.id),
                    organization_id=organization_id,
                    error_message="Email delivery is disabled or SMTP settings are incomplete.",
                )
                return

            result = self.email.send_message(
                to_email=recipient or "",
                subject=subject,
                body_text=body,
                metadata={"notification_id": str(notification.id), "event_type": event_type},
            )
            if str(result.get("status") or "").lower() == "skipped":
                self.notifications.mark_skipped(
                    notification_id=str(notification.id),
                    organization_id=organization_id,
                    error_message="Email delivery was skipped by the configured email service.",
                )
                return
            self.notifications.mark_sent(
                notification_id=str(notification.id),
                organization_id=organization_id,
                provider_message_id=str(result.get("provider_message_id") or ""),
            )
        except Exception:  # noqa: BLE001 - source actions must stay resilient.
            logger.exception(
                "Operational notification failed",
                extra={"event_type": event_type, "organization_id": organization_id},
            )
            try:
                if "notification" in locals():
                    self.notifications.mark_failed(
                        notification_id=str(notification.id),
                        organization_id=organization_id,
                        error_message="Email delivery failed.",
                    )
            except Exception:
                logger.exception("Failed to mark operational notification as failed")

    def _email_configured(self) -> bool:
        delivery_enabled = (
            self.settings.email_delivery_enabled or self.settings.email_sending_enabled
        )
        if not delivery_enabled:
            return False
        if not self.settings.email_enabled and self.settings.environment not in {
            "local",
            "development",
            "test",
        }:
            return False
        if self.settings.email_provider == "smtp":
            return bool(self.settings.smtp_host)
        return self.settings.environment in {"local", "development", "test"}

    def _ops_recipient(self) -> str | None:
        return self._clean(self.settings.ops_notification_email)

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _str(value: object | None) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _timestamp_label(value: object | None) -> str:
        if value is None:
            return "Not provided"
        isoformat = getattr(value, "isoformat", None)
        if callable(isoformat):
            return str(isoformat())
        return str(value)

    @staticmethod
    def _load_label(load: Load | None) -> str:
        if load is None:
            return "Unassigned load"
        return str(load.load_number or load.id)

    @staticmethod
    def _document_label(document: LoadDocument) -> str:
        document_type = getattr(document.document_type, "value", str(document.document_type))
        return document_type.replace("_", " ").title()
