from __future__ import annotations

from app.domain.enums.compat import StrEnum


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_REQUIRED = "not_required"
    NEEDS_REVIEW = "needs_review"
