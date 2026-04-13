from __future__ import annotations

from app.domain.enums.compat import StrEnum


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
    PAST_DUE = "past_due"