from __future__ import annotations

from app.domain.enums.compat import StrEnum


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    SKIPPED = "skipped"
    RECEIVED = "received"
