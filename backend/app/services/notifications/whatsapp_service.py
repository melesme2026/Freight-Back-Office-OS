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
        return {
            "channel": "whatsapp",
            "to_phone": to_phone,
            "subject": subject,
            "body_text": body_text,
            "provider_message_id": f"wa-{int(datetime.now(timezone.utc).timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }