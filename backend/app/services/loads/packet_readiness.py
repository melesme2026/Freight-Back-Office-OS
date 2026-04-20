from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.enums.document_type import DocumentType


@dataclass(frozen=True)
class ReadinessRuleSet:
    invoice_required: tuple[DocumentType, ...]
    submission_required: tuple[DocumentType, ...]
    recommended_for_submission: tuple[DocumentType, ...]


BASELINE_RULE_SET = ReadinessRuleSet(
    invoice_required=(
        DocumentType.RATE_CONFIRMATION,
        DocumentType.PROOF_OF_DELIVERY,
    ),
    submission_required=(
        DocumentType.RATE_CONFIRMATION,
        DocumentType.PROOF_OF_DELIVERY,
        DocumentType.INVOICE,
    ),
    recommended_for_submission=(
        DocumentType.BILL_OF_LADING,
    ),
)


READINESS_OPTIONAL_DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    DocumentType.BILL_OF_LADING,
    DocumentType.LUMPER_RECEIPT,
    DocumentType.DETENTION_SUPPORT,
    DocumentType.SCALE_TICKET,
    DocumentType.ACCESSORIAL_SUPPORT,
    DocumentType.PAYMENT_REMITTANCE,
    DocumentType.NOTICE_OF_ASSIGNMENT,
    DocumentType.W9,
    DocumentType.CERTIFICATE_OF_INSURANCE,
    DocumentType.DAMAGE_CLAIM_PHOTO,
    DocumentType.OTHER,
)


def _document_value(document_type: DocumentType) -> str:
    return document_type.value


def _present_values(document_types: Iterable[DocumentType]) -> set[str]:
    return {_document_value(document_type) for document_type in document_types}


def calculate_packet_readiness(
    *,
    document_types: Iterable[DocumentType],
    rule_set: ReadinessRuleSet = BASELINE_RULE_SET,
) -> dict[str, object]:
    present = _present_values(document_types)

    invoice_required_values = [_document_value(value) for value in rule_set.invoice_required]
    submission_required_values = [_document_value(value) for value in rule_set.submission_required]
    recommended_values = [_document_value(value) for value in rule_set.recommended_for_submission]

    present_invoice_required = sorted(value for value in invoice_required_values if value in present)
    missing_invoice_required = sorted(value for value in invoice_required_values if value not in present)

    present_submission_required = sorted(value for value in submission_required_values if value in present)
    missing_submission_required = sorted(value for value in submission_required_values if value not in present)

    optional_present = sorted(
        value
        for value in (_document_value(document_type) for document_type in READINESS_OPTIONAL_DOCUMENT_TYPES)
        if value in present
    )

    missing_recommended = sorted(value for value in recommended_values if value not in present)

    ready_for_invoice = not missing_invoice_required
    ready_to_submit = not missing_submission_required

    blockers: list[str] = []
    notes: list[str] = []

    if missing_invoice_required:
        blockers.append(
            "Missing invoice-readiness documents: " + ", ".join(missing_invoice_required)
        )
    if missing_submission_required:
        blockers.append(
            "Missing submission-required documents: " + ", ".join(missing_submission_required)
        )

    if missing_recommended:
        notes.append(
            "Recommended documents still missing: " + ", ".join(missing_recommended)
        )

    if ready_to_submit:
        readiness_state = "ready_to_submit"
    elif ready_for_invoice:
        readiness_state = "ready_for_invoice"
    elif len(present) > 0:
        readiness_state = "needs_documents"
    else:
        readiness_state = "missing_core_documents"

    return {
        "readiness_state": readiness_state,
        "ready_for_invoice": ready_for_invoice,
        "ready_to_submit": ready_to_submit,
        "present_documents": sorted(present),
        "required_documents": {
            "invoice": invoice_required_values,
            "submission": submission_required_values,
        },
        "present_required_documents": {
            "invoice": present_invoice_required,
            "submission": present_submission_required,
        },
        "missing_required_documents": {
            "invoice": missing_invoice_required,
            "submission": missing_submission_required,
        },
        "optional_documents_present": optional_present,
        "missing_recommended_documents": missing_recommended,
        "blockers": blockers,
        "notes": notes,
    }
