from __future__ import annotations

from app.services.validation.rules.amount_mismatch import AmountMismatchRule
from app.services.validation.rules.broker_consistency import BrokerConsistencyRule
from app.services.validation.rules.duplicate_load import DuplicateLoadRule
from app.services.validation.rules.missing_required_fields import MissingRequiredFieldsRule
from app.services.validation.rules.missing_signature import MissingSignatureRule
from app.services.validation.rules.unreadable_document import UnreadableDocumentRule


def test_missing_required_fields_rule_detects_missing_fields() -> None:
    rule = MissingRequiredFieldsRule()

    results = rule.evaluate(payload={"extracted_fields": []})

    assert len(results) == 1
    assert results[0]["rule_code"] == "missing_required_fields"
    assert results[0]["is_blocking"] is True


def test_missing_signature_rule_skips_non_delivery_documents() -> None:
    rule = MissingSignatureRule()

    results = rule.evaluate(
        payload={
            "document_type": "invoice",
            "extracted_fields": [],
        }
    )

    assert results == []


def test_missing_signature_rule_flags_missing_signature() -> None:
    rule = MissingSignatureRule()

    results = rule.evaluate(
        payload={
            "document_type": "bill_of_lading",
            "extracted_fields": [
                {"field_name": "signature_present", "field_value_text": "no"}
            ],
        }
    )

    assert len(results) == 1
    assert results[0]["rule_code"] == "missing_signature"
    assert results[0]["is_blocking"] is True


def test_amount_mismatch_rule_flags_difference() -> None:
    rule = AmountMismatchRule()

    results = rule.evaluate(
        payload={
            "gross_amount": "1000.00",
            "extracted_fields": [
                {"field_name": "invoice_amount", "field_value_number": "900.00"},
            ],
        }
    )

    assert len(results) == 1
    assert results[0]["rule_code"] == "amount_mismatch"


def test_duplicate_load_rule_flags_candidates() -> None:
    rule = DuplicateLoadRule()

    results = rule.evaluate(
        payload={
            "duplicate_candidates": [{"load_id": "abc", "score": 100}],
        }
    )

    assert len(results) == 1
    assert results[0]["rule_code"] == "duplicate_load"


def test_unreadable_document_rule_flags_empty_ocr_and_fields() -> None:
    rule = UnreadableDocumentRule()

    results = rule.evaluate(
        payload={
            "ocr_text": "",
            "extracted_fields": [],
        }
    )

    assert len(results) == 1
    assert results[0]["rule_code"] == "unreadable_document"
    assert results[0]["is_blocking"] is True


def test_broker_consistency_rule_flags_name_mismatch() -> None:
    rule = BrokerConsistencyRule()

    results = rule.evaluate(
        payload={
            "broker_name_raw": "Alpha Logistics",
            "extracted_fields": [
                {"field_name": "broker_name", "field_value_text": "Beta Logistics"}
            ],
        }
    )

    assert len(results) == 1
    assert results[0]["rule_code"] == "broker_consistency"