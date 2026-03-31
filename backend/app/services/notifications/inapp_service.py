from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InAppService:
    def send_message(
        self,
        *,
        recipient_id: str,
        title: str | None,
        body_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sent_at = datetime.now(timezone.utc)
        normalized_recipient_id = recipient_id.strip()
        normalized_title = title.strip() if title is not None else None

        return {
            "channel": "in_app",
            "recipient_id": normalized_recipient_id,
            "title": normalized_title,
            "body_text": body_text,
            "provider_message_id": f"inapp-{int(sent_at.timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": sent_at.isoformat(),
        }