from __future__ import annotations

from enum import StrEnum


class PaymentProvider(StrEnum):
    STRIPE = "stripe"
    MANUAL = "manual"
    OTHER = "other"
    NONE = "none"