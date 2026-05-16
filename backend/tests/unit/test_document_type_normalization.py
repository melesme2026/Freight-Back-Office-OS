from app.domain.enums.document_type import (
    DocumentType,
    canonical_document_type,
    normalize_document_type_value,
)
from app.services.loads.packet_readiness import calculate_packet_readiness


def test_canonical_document_type_aliases_cover_submission_documents() -> None:
    aliases = [
        "proof_of_delivery",
        "pod",
        "delivery_receipt",
        "delivery receipt",
        "Proof of Delivery",
        "POD",
        "signed_pod",
    ]

    for alias in aliases:
        assert normalize_document_type_value(alias) == DocumentType.PROOF_OF_DELIVERY
        assert canonical_document_type(alias) == "proof_of_delivery"


def test_packet_readiness_treats_pod_alias_as_proof_of_delivery() -> None:
    readiness = calculate_packet_readiness(
        document_types=["ratecon", "POD", "generated_invoice"]
    )

    assert readiness["ready_to_submit"] is True
    assert readiness["missing_required_documents"]["submission"] == []
    assert readiness["present_documents"] == [
        "invoice",
        "proof_of_delivery",
        "rate_confirmation",
    ]
