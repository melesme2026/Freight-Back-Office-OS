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
        "proof-of-delivery",
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


def test_required_document_aliases_normalize_to_canonical_values() -> None:
    aliases = {
        "proof_of_delivery": DocumentType.PROOF_OF_DELIVERY,
        "Proof of Delivery": DocumentType.PROOF_OF_DELIVERY,
        "proof-of-delivery": DocumentType.PROOF_OF_DELIVERY,
        "pod": DocumentType.PROOF_OF_DELIVERY,
        "POD": DocumentType.PROOF_OF_DELIVERY,
        "delivery_receipt": DocumentType.PROOF_OF_DELIVERY,
        "signed_pod": DocumentType.PROOF_OF_DELIVERY,
        "bill_of_lading": DocumentType.BILL_OF_LADING,
        "Bill of Lading": DocumentType.BILL_OF_LADING,
        "bol": DocumentType.BILL_OF_LADING,
        "BOL": DocumentType.BILL_OF_LADING,
        "rate_confirmation": DocumentType.RATE_CONFIRMATION,
        "ratecon": DocumentType.RATE_CONFIRMATION,
        "Rate Confirmation": DocumentType.RATE_CONFIRMATION,
        "invoice": DocumentType.INVOICE,
        "Invoice": DocumentType.INVOICE,
    }

    for alias, expected in aliases.items():
        assert normalize_document_type_value(alias) == expected
        assert canonical_document_type(alias) == expected.value
