from __future__ import annotations

from app.domain.enums.compat import StrEnum


class LoadPaymentStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    AWAITING_PAYMENT = "awaiting_payment"
    PARTIALLY_PAID = "partially_paid"
    ADVANCE_PAID = "advance_paid"
    RESERVE_PENDING = "reserve_pending"
    PAID = "paid"
    SHORT_PAID = "short_paid"
    DISPUTED = "disputed"
