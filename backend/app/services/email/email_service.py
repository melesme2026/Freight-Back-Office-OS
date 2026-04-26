from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any, TypedDict

from app.core.config import get_settings


class EmailAttachment(TypedDict):
    filename: str
    content_type: str
    bytes: bytes


class PacketEmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.email_sending_enabled)

    def validate_email_config(self) -> tuple[bool, str | None]:
        if not self.is_enabled():
            return False, "Email sending is disabled. Download the packet ZIP or copy the submission email instead."

        provider = (self.settings.email_provider or "").strip().lower()
        if provider not in {"smtp", "sendgrid"}:
            return False, "Email sending provider is not configured."

        if not (self.settings.email_from_address or "").strip():
            return False, "EMAIL_FROM_ADDRESS is required for packet email sending."

        if provider == "smtp":
            if not (self.settings.smtp_host or "").strip():
                return False, "SMTP_HOST is required for SMTP packet email sending."
            if not self.settings.smtp_port:
                return False, "SMTP_PORT is required for SMTP packet email sending."
            return True, None

        if provider == "sendgrid":
            if not (self.settings.sendgrid_api_key or "").strip():
                return False, "SENDGRID_API_KEY is required for SendGrid packet email sending."
            return True, None

        return False, "Email sending provider is not configured."

    def send_email_with_attachments(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        attachments: list[EmailAttachment],
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        config_valid, config_error = self.validate_email_config()
        provider = (self.settings.email_provider or "").strip().lower()

        if not config_valid:
            return {
                "provider": provider or "none",
                "accepted": False,
                "provider_message_id": None,
                "error_message": config_error,
            }

        normalized_to = (to or "").strip().lower()
        normalized_subject = (subject or "").strip()
        normalized_body = (body or "").strip()
        if not normalized_to or not normalized_subject or not normalized_body:
            return {
                "provider": provider,
                "accepted": False,
                "provider_message_id": None,
                "error_message": "to, subject, and body are required",
            }

        if provider == "sendgrid":
            return {
                "provider": provider,
                "accepted": False,
                "provider_message_id": None,
                "error_message": "SendGrid provider is not yet implemented for packet email sending.",
            }

        try:
            message = EmailMessage()
            from_address = (self.settings.email_from_address or "").strip()
            from_name = (self.settings.email_from_name or "").strip()
            message["From"] = f"{from_name} <{from_address}>" if from_name else from_address
            message["To"] = normalized_to
            if cc:
                message["Cc"] = ", ".join([item.strip().lower() for item in cc if item.strip()])
            message["Subject"] = normalized_subject
            message.set_content(normalized_body)

            recipients = [normalized_to]
            recipients.extend([item.strip().lower() for item in (cc or []) if item.strip()])
            recipients.extend([item.strip().lower() for item in (bcc or []) if item.strip()])

            for attachment in attachments:
                content_type = (attachment.get("content_type") or "application/octet-stream").strip()
                maintype, _, subtype = content_type.partition("/")
                if not subtype:
                    maintype, subtype = "application", "octet-stream"
                message.add_attachment(
                    attachment.get("bytes") or b"",
                    maintype=maintype,
                    subtype=subtype,
                    filename=(attachment.get("filename") or "attachment.bin").strip() or "attachment.bin",
                )

            with smtplib.SMTP(host=self.settings.smtp_host, port=self.settings.smtp_port, timeout=20) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message, to_addrs=recipients)

            return {
                "provider": provider,
                "accepted": True,
                "provider_message_id": None,
                "error_message": None,
            }
        except Exception:
            return {
                "provider": provider,
                "accepted": False,
                "provider_message_id": None,
                "error_message": "Email provider send failed.",
            }
