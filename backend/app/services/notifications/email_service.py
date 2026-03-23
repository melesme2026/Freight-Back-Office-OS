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
        return {
            "channel": "email",
            "to_email": to_email,
            "subject": subject,
            "body_text": body_text,
            "provider_message_id": f"em-{int(datetime.now(timezone.utc).timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }