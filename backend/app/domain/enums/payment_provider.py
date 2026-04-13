from __future__ import annotations

from app.domain.enums.compat import StrEnum


class PaymentProvider(StrEnum):
    STRIPE = "stripe"
    MANUAL = "manual"
    OTHER = "other"
    NONE = "none"