from __future__ import annotations

from app.domain.enums.compat import StrEnum


class FactoringWorkflowStatus(StrEnum):
    NOT_FACTORED = "not_factored"
    SUBMITTED_TO_FACTORING = "submitted_to_factoring"
    FUNDED = "funded"
    PARTIALLY_PAID = "partially_paid"
    RESERVE_PENDING = "reserve_pending"
    RECONCILED = "reconciled"
    DISPUTED = "disputed"


class FactoringReconciliationStatus(StrEnum):
    UNRECONCILED = "unreconciled"
    PARTIALLY_RECONCILED = "partially_reconciled"
    RECONCILED = "reconciled"


class FactoringAgingBucket(StrEnum):
    CURRENT = "current"
    DAYS_1_15 = "1_15_days"
    DAYS_16_30 = "16_30_days"
    DAYS_31_60 = "31_60_days"
    DAYS_60_PLUS = "60_plus_days"
