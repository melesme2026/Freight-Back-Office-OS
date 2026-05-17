from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.domain.enums.document_type import DocumentType, normalize_document_type_value
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from sqlalchemy import select, update
from sqlalchemy.orm import Session


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
    recommended_for_submission=(DocumentType.BILL_OF_LADING,),
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


def _present_values(document_types: Iterable[DocumentType | str | None]) -> set[str]:
    present: set[str] = set()
    for document_type in document_types:
        normalized = normalize_document_type_value(document_type, allow_none=True)
        if normalized is not None and normalized != DocumentType.UNKNOWN:
            present.add(normalized.value)
    return present


def _loaded_document_types(load: Any) -> list[DocumentType | str | None] | None:
    loaded_values = getattr(load, "__dict__", {})
    documents = loaded_values.get("documents")
    if not isinstance(documents, list):
        return None
    return [getattr(document, "document_type", None) for document in documents]


def get_load_document_types_from_table(
    *, db: Session, load_id: str
) -> list[DocumentType | str | None]:
    """Return the actual attached document types for a load.

    This is the canonical source of truth for readiness. Persisted load flags or
    older missing-doc snapshots are intentionally not used here because document
    delete/reupload flows can make those snapshots stale.
    """

    return list(
        db.scalars(
            select(LoadDocument.document_type)
            .where(LoadDocument.load_id == load_id)
            .execution_options(populate_existing=False)
        ).all()
    )


def calculate_load_packet_readiness(
    *,
    load: Any,
    db: Session | None = None,
    allow_flag_fallback: bool = False,
    rule_set: ReadinessRuleSet = BASELINE_RULE_SET,
) -> dict[str, object]:
    """Calculate canonical packet readiness for any load surface.

    Staff, driver portal, submission packet, factoring, and invoice views should
    call this helper instead of rebuilding readiness from load flags. Actual
    attached documents win over any cached readiness or missing-doc snapshot.
    """

    document_types = None
    if db is not None and getattr(load, "id", None):
        document_types = get_load_document_types_from_table(db=db, load_id=str(load.id))
    if document_types is None:
        document_types = _loaded_document_types(load)

    if document_types is None and allow_flag_fallback:
        document_types = []
        if getattr(load, "has_ratecon", False):
            document_types.append(DocumentType.RATE_CONFIRMATION)
        if getattr(load, "has_bol", False):
            document_types.append(DocumentType.BILL_OF_LADING)
        if getattr(load, "has_invoice", False):
            document_types.append(DocumentType.INVOICE)

    return calculate_packet_readiness(
        document_types=document_types or [],
        rule_set=rule_set,
    )


def sync_load_document_readiness(*, db: Session, load_id: str) -> dict[str, object]:
    """Synchronize denormalized load document flags from canonical readiness."""

    readiness = calculate_packet_readiness(
        document_types=get_load_document_types_from_table(db=db, load_id=load_id)
    )
    present_values = set(readiness["present_documents"])
    db.execute(
        update(Load)
        .where(Load.id == load_id)
        .values(
            has_ratecon=DocumentType.RATE_CONFIRMATION.value in present_values,
            has_bol=DocumentType.BILL_OF_LADING.value in present_values,
            has_invoice=DocumentType.INVOICE.value in present_values,
            documents_complete=bool(readiness["ready_to_submit"]),
        )
        .execution_options(synchronize_session=False)
    )
    return readiness


def calculate_organization_readiness_counts(
    *, db: Session, organization_id: str
) -> dict[str, int]:
    """Aggregate load readiness from actual attached documents.

    This is intentionally document-table based so dashboard KPIs cannot be
    overridden by stale denormalized load flags or older readiness snapshots.
    """

    load_ids = list(
        db.scalars(select(Load.id).where(Load.organization_id == organization_id)).all()
    )
    if not load_ids:
        return {
            "loads_ready_for_invoice": 0,
            "loads_ready_to_submit": 0,
            "loads_missing_documents": 0,
        }

    documents_by_load_id: dict[object, list[DocumentType | str | None]] = {
        load_id: [] for load_id in load_ids
    }
    rows = db.execute(
        select(LoadDocument.load_id, LoadDocument.document_type).where(
            LoadDocument.organization_id == organization_id,
            LoadDocument.load_id.in_(load_ids),
        )
    ).all()
    for load_id, document_type in rows:
        documents_by_load_id.setdefault(load_id, []).append(document_type)

    ready_for_invoice = 0
    ready_to_submit = 0
    missing_documents = 0
    for document_types in documents_by_load_id.values():
        readiness = calculate_packet_readiness(document_types=document_types)
        if readiness["ready_for_invoice"]:
            ready_for_invoice += 1
        if readiness["ready_to_submit"]:
            ready_to_submit += 1
        if readiness["missing_required_documents"]["submission"]:
            missing_documents += 1

    return {
        "loads_ready_for_invoice": ready_for_invoice,
        "loads_ready_to_submit": ready_to_submit,
        "loads_missing_documents": missing_documents,
    }


def calculate_packet_readiness(
    *,
    document_types: Iterable[DocumentType | str | None],
    rule_set: ReadinessRuleSet = BASELINE_RULE_SET,
) -> dict[str, object]:
    present = _present_values(document_types)

    invoice_required_values = [
        _document_value(value) for value in rule_set.invoice_required
    ]
    submission_required_values = [
        _document_value(value) for value in rule_set.submission_required
    ]
    recommended_values = [
        _document_value(value) for value in rule_set.recommended_for_submission
    ]

    present_invoice_required = sorted(
        value for value in invoice_required_values if value in present
    )
    missing_invoice_required = sorted(
        value for value in invoice_required_values if value not in present
    )

    present_submission_required = sorted(
        value for value in submission_required_values if value in present
    )
    missing_submission_required = sorted(
        value for value in submission_required_values if value not in present
    )

    optional_present = sorted(
        value
        for value in (
            _document_value(document_type)
            for document_type in READINESS_OPTIONAL_DOCUMENT_TYPES
        )
        if value in present
    )

    missing_recommended = sorted(
        value for value in recommended_values if value not in present
    )

    ready_for_invoice = not missing_invoice_required
    ready_to_submit = not missing_submission_required

    blockers: list[str] = []
    notes: list[str] = []

    if missing_invoice_required:
        blockers.append(
            "Missing invoice-readiness documents: "
            + ", ".join(missing_invoice_required)
        )
    if missing_submission_required:
        blockers.append(
            "Missing submission-required documents: "
            + ", ".join(missing_submission_required)
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
