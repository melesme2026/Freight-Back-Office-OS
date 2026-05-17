from __future__ import annotations

from app.domain.enums.validation_severity import ValidationSeverity
from app.services.validation.validation_issue_generator import ValidationIssueGenerator


def test_wrong_document_upload_creates_explainable_review_issue(db_session) -> None:
    generator = ValidationIssueGenerator(db_session)

    issues = generator.generate(
        organization_id="00000000-0000-0000-0000-000000000701",
        load_id="00000000-0000-0000-0000-000000000702",
        document_id=None,
        payload={
            "document_type": "proof_of_delivery",
            "detected_document_type": "bill_of_lading",
            "extraction_confidence": 0.44,
            "required_fields": ["delivery_date", "signed_by"],
            "extracted_fields": {"delivery_date": "2026-05-17"},
        },
    )

    rule_codes = {issue.rule_code for issue in issues}
    assert "wrong_document_classification" in rule_codes
    assert "low_extraction_confidence" in rule_codes
    assert "missing_critical_extracted_values" in rule_codes
    assert any(issue.severity == ValidationSeverity.ERROR for issue in issues)
    assert any("Remediation:" in issue.description for issue in issues)


def test_validation_issue_generator_deduplicates_open_issues(db_session) -> None:
    generator = ValidationIssueGenerator(db_session)
    payload = {"document_type": "pod", "detected_document_type": "bol"}

    first = generator.generate(
        organization_id="00000000-0000-0000-0000-000000000711",
        load_id="00000000-0000-0000-0000-000000000712",
        document_id=None,
        payload=payload,
    )
    second = generator.generate(
        organization_id="00000000-0000-0000-0000-000000000711",
        load_id="00000000-0000-0000-0000-000000000712",
        document_id=None,
        payload=payload,
    )

    assert len(first) == 1
    assert second == []
