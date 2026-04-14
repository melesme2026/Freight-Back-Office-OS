from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ValidationError


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_message(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sent_at = datetime.now(timezone.utc)
        normalized_to_email = to_email.strip().lower()
        normalized_subject = subject.strip()
        normalized_body = body_text.strip()

        if not normalized_to_email:
            raise ValidationError("to_email is required")
        if not normalized_subject:
            raise ValidationError("subject is required")
        if not normalized_body:
            raise ValidationError("body_text is required")

        if not self.settings.email_enabled:
            if self.settings.environment in {"local", "development", "test"}:
                return {
                    "channel": "email",
                    "to_email": normalized_to_email,
                    "subject": normalized_subject,
                    "body_text": normalized_body,
                    "provider_message_id": f"dev-email-{int(sent_at.timestamp())}",
                    "status": "skipped",
                    "metadata": metadata or {},
                    "sent_at": sent_at.isoformat(),
                }
            raise ValidationError("Email delivery is disabled in this environment")

        provider = self.settings.email_provider
        if provider != "smtp":
            raise ValidationError(
                "Unsupported configured email provider",
                details={"email_provider": provider},
            )

        smtp_host = self.settings.smtp_host
        if not smtp_host:
            raise ValidationError("smtp_host is required for smtp email delivery")

        msg = EmailMessage()
        msg["From"] = self.settings.default_from_email
        msg["To"] = normalized_to_email
        msg["Subject"] = normalized_subject
        msg.set_content(normalized_body)

        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                host=smtp_host,
                port=self.settings.smtp_port,
                timeout=15,
            ) as smtp:
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(
                host=smtp_host,
                port=self.settings.smtp_port,
                timeout=15,
            ) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(msg)

        return {
            "channel": "email",
            "to_email": normalized_to_email,
            "subject": normalized_subject,
            "body_text": normalized_body,
            "provider_message_id": f"smtp-{int(sent_at.timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": sent_at.isoformat(),
        }
