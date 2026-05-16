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


_CANONICAL_DOCUMENT_TYPE_ALIASES: dict[str, DocumentType] = {
    "unknown": DocumentType.UNKNOWN,
    "rate confirmation": DocumentType.RATE_CONFIRMATION,
    "rate_confirmation": DocumentType.RATE_CONFIRMATION,
    "rate-confirmation": DocumentType.RATE_CONFIRMATION,
    "rate_confirmation_pdf": DocumentType.RATE_CONFIRMATION,
    "rate confirmation pdf": DocumentType.RATE_CONFIRMATION,
    "ratecon": DocumentType.RATE_CONFIRMATION,
    "rate con": DocumentType.RATE_CONFIRMATION,
    "rc": DocumentType.RATE_CONFIRMATION,
    "bill of lading": DocumentType.BILL_OF_LADING,
    "bill_of_lading": DocumentType.BILL_OF_LADING,
    "bill-of-lading": DocumentType.BILL_OF_LADING,
    "bol": DocumentType.BILL_OF_LADING,
    "proof of delivery": DocumentType.PROOF_OF_DELIVERY,
    "proof_of_delivery": DocumentType.PROOF_OF_DELIVERY,
    "proof-of-delivery": DocumentType.PROOF_OF_DELIVERY,
    "pod": DocumentType.PROOF_OF_DELIVERY,
    "delivery_receipt": DocumentType.PROOF_OF_DELIVERY,
    "delivery receipt": DocumentType.PROOF_OF_DELIVERY,
    "signed_pod": DocumentType.PROOF_OF_DELIVERY,
    "signed pod": DocumentType.PROOF_OF_DELIVERY,
    "invoice": DocumentType.INVOICE,
    "freight_invoice": DocumentType.INVOICE,
    "freight invoice": DocumentType.INVOICE,
    "generated_invoice": DocumentType.INVOICE,
    "generated invoice": DocumentType.INVOICE,
    "lumper receipt": DocumentType.LUMPER_RECEIPT,
    "lumper_receipt": DocumentType.LUMPER_RECEIPT,
    "detention support": DocumentType.DETENTION_SUPPORT,
    "detention_support": DocumentType.DETENTION_SUPPORT,
    "detention approval": DocumentType.DETENTION_SUPPORT,
    "detention_approval": DocumentType.DETENTION_SUPPORT,
    "scale ticket": DocumentType.SCALE_TICKET,
    "scale_ticket": DocumentType.SCALE_TICKET,
    "accessorial support": DocumentType.ACCESSORIAL_SUPPORT,
    "accessorial_support": DocumentType.ACCESSORIAL_SUPPORT,
    "accessorial approval": DocumentType.ACCESSORIAL_SUPPORT,
    "accessorial_approval": DocumentType.ACCESSORIAL_SUPPORT,
    "payment remittance": DocumentType.PAYMENT_REMITTANCE,
    "payment_remittance": DocumentType.PAYMENT_REMITTANCE,
    "fuel/expense receipt": DocumentType.PAYMENT_REMITTANCE,
    "fuel expense receipt": DocumentType.PAYMENT_REMITTANCE,
    "fuel_expense_receipt": DocumentType.PAYMENT_REMITTANCE,
    "notice of assignment": DocumentType.NOTICE_OF_ASSIGNMENT,
    "notice_of_assignment": DocumentType.NOTICE_OF_ASSIGNMENT,
    "w9": DocumentType.W9,
    "w-9": DocumentType.W9,
    "certificate of insurance": DocumentType.CERTIFICATE_OF_INSURANCE,
    "certificate_insurance": DocumentType.CERTIFICATE_OF_INSURANCE,
    "certificate_of_insurance": DocumentType.CERTIFICATE_OF_INSURANCE,
    "damage claim photo": DocumentType.DAMAGE_CLAIM_PHOTO,
    "damage_claim_photo": DocumentType.DAMAGE_CLAIM_PHOTO,
    "other": DocumentType.OTHER,
}


def normalize_document_type_value(
    value: str | DocumentType | None, *, allow_none: bool = False
) -> DocumentType | None:
    if value is None:
        return None if allow_none else DocumentType.UNKNOWN
    if isinstance(value, DocumentType):
        return value

    normalized = str(value).strip().lower().replace(".", " ")
    normalized = " ".join(normalized.replace("/", " ").split())
    if not normalized:
        return None if allow_none else DocumentType.UNKNOWN

    candidates = {
        normalized,
        normalized.replace(" ", "_"),
        normalized.replace(" ", "-"),
        normalized.replace("-", "_"),
        normalized.replace("_", " "),
    }
    for candidate in candidates:
        if candidate in _CANONICAL_DOCUMENT_TYPE_ALIASES:
            return _CANONICAL_DOCUMENT_TYPE_ALIASES[candidate]

    try:
        return DocumentType(normalized)
    except ValueError:
        return None if allow_none else DocumentType.UNKNOWN


def canonical_document_type(value: str | DocumentType | None, *, default: str = "unknown") -> str:
    normalized = normalize_document_type_value(value, allow_none=True)
    return normalized.value if normalized is not None else default
