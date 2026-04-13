from __future__ import annotations

from app.domain.enums.compat import StrEnum


class DocumentType(StrEnum):
    RATE_CONFIRMATION = "rate_confirmation"
    BILL_OF_LADING = "bill_of_lading"
    INVOICE = "invoice"
    PROOF_OF_DELIVERY = "proof_of_delivery"
    OTHER = "other"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object):
        if value == "bol":
            return cls.BILL_OF_LADING
        if value == "pod":
            return cls.PROOF_OF_DELIVERY
        return cls.UNKNOWN