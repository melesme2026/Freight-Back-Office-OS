from __future__ import annotations

from app.domain.enums.compat import StrEnum


class DocumentType(StrEnum):
    RATE_CONFIRMATION = "rate_confirmation"
    BILL_OF_LADING = "bill_of_lading"
    PROOF_OF_DELIVERY = "proof_of_delivery"
    INVOICE = "invoice"
    LUMPER_RECEIPT = "lumper_receipt"
    DETENTION_SUPPORT = "detention_support"
    SCALE_TICKET = "scale_ticket"
    ACCESSORIAL_SUPPORT = "accessorial_support"
    PAYMENT_REMITTANCE = "payment_remittance"
    NOTICE_OF_ASSIGNMENT = "notice_of_assignment"
    W9 = "w9"
    CERTIFICATE_OF_INSURANCE = "certificate_of_insurance"
    DAMAGE_CLAIM_PHOTO = "damage_claim_photo"
    OTHER = "other"
    UNKNOWN = "unknown"