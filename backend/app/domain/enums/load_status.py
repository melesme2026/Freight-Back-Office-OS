from __future__ import annotations

from enum import StrEnum


class LoadStatus(StrEnum):
    NEW = "new"
    DOCS_RECEIVED = "docs_received"
    EXTRACTING = "extracting"
    NEEDS_REVIEW = "needs_review"
    VALIDATED = "validated"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    FUNDED = "funded"
    PAID = "paid"
    EXCEPTION = "exception"
    ARCHIVED = "archived"