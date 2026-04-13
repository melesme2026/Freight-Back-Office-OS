from __future__ import annotations

from app.domain.enums.compat import StrEnum


class DocumentType(StrEnum):
    RATE_CONFIRMATION = "rate_confirmation"
    BILL_OF_LADING = "bill_of_lading"
    INVOICE = "invoice"
    PROOF_OF_DELIVERY = "proof_of_delivery"
    OTHER = "other"
    UNKNOWN = "unknown"