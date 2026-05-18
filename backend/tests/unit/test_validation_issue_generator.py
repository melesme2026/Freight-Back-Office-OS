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


def test_low_extraction_confidence_preserves_zero_value() -> None:
    issues = ValidationIssueGenerator(db=None).evaluate(  # type: ignore[arg-type]
        payload={
            "document_type": "proof_of_delivery",
            "extraction_confidence": 0.0,
            "classification_confidence": 0.99,
        }
    )

    assert any(issue.rule_code == "low_extraction_confidence" for issue in issues)


def test_orchestrator_suppresses_existing_open_legacy_duplicate(db_session) -> None:
    from app.domain.models.validation_issue import ValidationIssue
    from app.services.validation.validation_orchestrator import ValidationOrchestrator

    organization_id = "00000000-0000-0000-0000-000000000721"
    load_id = "00000000-0000-0000-0000-000000000722"
    db_session.add(
        ValidationIssue(
            organization_id=organization_id,
            load_id=load_id,
            document_id=None,
            rule_code="unreadable_document",
            severity=ValidationSeverity.CRITICAL,
            title="Unreadable or corrupt document",
            description="The document could not be opened or read reliably.",
            is_blocking=True,
            is_resolved=False,
        )
    )
    db_session.flush()

    issues = ValidationOrchestrator(db_session).validate_load(
        organization_id=organization_id,
        load_id=load_id,
        document_id=None,
        payload={"document_type": "proof_of_delivery", "unreadable": True},
    )

    assert all(issue.rule_code != "unreadable_document" for issue in issues)
    open_issues = db_session.query(ValidationIssue).filter_by(
        organization_id=organization_id,
        load_id=load_id,
        rule_code="unreadable_document",
        is_resolved=False,
    )
    assert open_issues.count() == 1
