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
        return {
            "channel": "in_app",
            "recipient_id": recipient_id,
            "title": title,
            "body_text": body_text,
            "provider_message_id": f"inapp-{int(datetime.now(timezone.utc).timestamp())}",
            "status": "sent",
            "metadata": metadata or {},
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }