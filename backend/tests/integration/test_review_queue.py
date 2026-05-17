from __future__ import annotations

from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.validation_issue import ValidationIssue
from app.services.loads.load_service import LoadService
from app.services.review.review_queue_service import ReviewQueueService


def test_review_queue_includes_loads_with_unresolved_issues(db_session) -> None:
    load_service = LoadService(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000501",
        customer_account_id="00000000-0000-0000-0000-000000000502",
        driver_id="00000000-0000-0000-0000-000000000503",
        load_number="RQ-1001",
    )

    issue = ValidationIssue(
        organization_id=load.organization_id,
        load_id=load.id,
        document_id=None,
        rule_code="missing_required_fields",
        severity=ValidationSeverity.ERROR,
        title="Missing required fields",
        description="Required extracted fields are missing.",
        is_blocking=True,
        is_resolved=False,
        resolved_by_staff_user_id=None,
        resolved_at=None,
        resolution_notes=None,
    )
    db_session.add(issue)
    db_session.commit()

    service = ReviewQueueService(db_session)
    result = service.get_review_queue(
        organization_id=str(load.organization_id),
        page=1,
        page_size=25,
    )

    assert result["total"] >= 1
    assert any(item["load_id"] == str(load.id) for item in result["items"])


def test_review_queue_empty_org_returns_without_hydration(db_session) -> None:
    service = ReviewQueueService(db_session)

    result = service.get_review_queue(
        organization_id="00000000-0000-0000-0000-000000000599",
        page=1,
        page_size=25,
    )

    assert result == {"items": [], "total": 0, "page": 1, "page_size": 25}


def test_review_queue_paginates_distinct_loads(db_session) -> None:
    load_service = LoadService(db_session)
    org_id = "00000000-0000-0000-0000-000000000581"
    load_ids = []
    for index in range(3):
        load = load_service.create_load(
            organization_id=org_id,
            customer_account_id="00000000-0000-0000-0000-000000000582",
            driver_id="00000000-0000-0000-0000-000000000583",
            load_number=f"RQ-PAGE-{index}",
        )
        load_ids.append(str(load.id))
        db_session.add(
            ValidationIssue(
                organization_id=load.organization_id,
                load_id=load.id,
                document_id=None,
                rule_code="validation_mismatch",
                severity=ValidationSeverity.ERROR,
                title="Validation mismatch",
                description="Mismatch.",
                is_blocking=True,
                is_resolved=False,
            )
        )
    db_session.commit()

    service = ReviewQueueService(db_session)
    first_page = service.get_review_queue(organization_id=org_id, page=1, page_size=2)
    second_page = service.get_review_queue(organization_id=org_id, page=2, page_size=2)

    assert first_page["total"] == 3
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 1
    assert {item["load_id"] for item in first_page["items"]}.isdisjoint(
        {item["load_id"] for item in second_page["items"]}
    )
