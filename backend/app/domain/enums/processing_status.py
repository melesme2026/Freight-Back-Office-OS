from __future__ import annotations

from enum import StrEnum


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"