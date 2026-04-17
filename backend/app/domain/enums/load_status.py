from __future__ import annotations

from app.domain.enums.compat import StrEnum


class LoadStatus(StrEnum):
    NEW = "new"
    DOCS_RECEIVED = "docs_received"
    NEEDS_REVIEW = "needs_review"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED_TO_BROKER = "submitted_to_broker"
    WAITING_ON_BROKER = "waiting_on_broker"
    SUBMITTED_TO_FACTORING = "submitted_to_factoring"
    WAITING_ON_FUNDING = "waiting_on_funding"
    FUNDED = "funded"
    PAID = "paid"
    EXCEPTION = "exception"
    ARCHIVED = "archived"
