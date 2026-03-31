from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class EmailService:
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

        return {
            "channel": "email",
            "to_email": normalized_to_email,
            "subject": subject,
            "body_text": body_text,
            "provider_message_id": f"em-{int(sent_at.timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": sent_at.isoformat(),
        }