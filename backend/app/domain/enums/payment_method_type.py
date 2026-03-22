from __future__ import annotations

from enum import StrEnum


class PaymentMethodType(StrEnum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    MANUAL = "manual"