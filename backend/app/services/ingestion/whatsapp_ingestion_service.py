from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WhatsAppIngestionService:
    def ingest(
        self,
        payload: dict[str, Any],
        request_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "accepted": True,
            "channel": "whatsapp",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "request_metadata": request_metadata or {},
            "payload": payload,
        }
