from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WhatsAppIngestionService:
    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "accepted": True,
            "channel": "whatsapp",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }