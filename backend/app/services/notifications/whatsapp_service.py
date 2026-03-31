from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WhatsAppService:
    def send_message(
        self,
        *,
        to_phone: str,
        body_text: str,
        subject: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sent_at = datetime.now(timezone.utc)
        normalized_to_phone = to_phone.strip()
        normalized_subject = subject.strip() if subject is not None else None

        return {
            "channel": "whatsapp",
            "to_phone": normalized_to_phone,
            "subject": normalized_subject,
            "body_text": body_text,
            "provider_message_id": f"wa-{int(sent_at.timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": sent_at.isoformat(),
        }