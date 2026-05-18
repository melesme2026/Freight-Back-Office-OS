from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from app.api.v1 import documents as documents_api
from app.domain.enums.channel import Channel
from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.enums.document_type import DocumentType
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.validation_issue import ValidationIssue
from app.services.onboarding.customer_account_service import CustomerAccountService
from app.services.review.review_queue_service import ReviewQueueService


def test_review_queue_empty_state_returns_without_load_hydration(db_session) -> None:
    org_id = uuid.uuid4()

    started_at = time.perf_counter()
    result = ReviewQueueService(db_session).get_review_queue(
        organization_id=str(org_id), page=1, page_size=25
    )
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert result == {"items": [], "total": 0, "page": 1, "page_size": 25}
    assert elapsed_ms < 1000


def test_customer_accounts_list_paginates_org_scoped_without_relationships(db_session) -> None:
    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    for index in range(3):
        db_session.add(
            CustomerAccount(
                organization_id=org_id,
                account_name=f"Org customer {index}",
                account_code=f"ORG-{index}",
                status=CustomerAccountStatus.ACTIVE,
            )
        )
    db_session.add(
        CustomerAccount(
            organization_id=other_org_id,
            account_name="Other org customer",
            account_code="OTHER-1",
            status=CustomerAccountStatus.ACTIVE,
        )
    )
    db_session.flush()

    items, total = CustomerAccountService(db_session).list_customer_accounts(
        organization_id=str(org_id), page=1, page_size=2
    )

    assert total == 3
    assert len(items) == 2
    assert {str(item.organization_id) for item in items} == {str(org_id)}
    assert all(item.loads == [] for item in items)


def test_document_detail_metadata_serializer_does_not_require_preview_or_ocr() -> None:
    document = LoadDocument(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_account_id=uuid.uuid4(),
        load_id=uuid.uuid4(),
        source_channel=Channel.MANUAL,
        document_type=DocumentType.INVOICE,
        original_filename="invoice.pdf",
        mime_type="application/pdf",
        file_size_bytes=1234,
        storage_key="uploaded/invoice.pdf",
        file_hash_sha256="c" * 64,
        received_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.QUEUED,
    )

    payload = documents_api._serialize_document_metadata(
        document, validation_issue_count=0
    )

    assert payload["id"] == str(document.id)
    assert payload["filename"] == "invoice.pdf"
    assert payload["download_available"] is True
    assert payload["preview_available"] is False
    assert payload["validation_summary"] == {
        "issue_count": 0,
        "status": "not_required",
    }
    assert "extracted_fields" not in payload
    assert "preview_text" not in payload


def test_review_queue_issue_first_pagination_metadata_correct(db_session) -> None:
    org_id = uuid.uuid4()
    load_ids = [uuid.uuid4(), uuid.uuid4()]
    for index, load_id in enumerate(load_ids):
        db_session.add(
            Load(
                id=load_id,
                organization_id=org_id,
                customer_account_id=uuid.uuid4(),
                driver_id=uuid.uuid4(),
                source_channel=Channel.MANUAL,
                status=LoadStatus.BOOKED,
                processing_status=ProcessingStatus.PENDING,
                load_number=f"RQ-{index}",
                currency_code="USD",
            )
        )
        db_session.add(
            ValidationIssue(
                organization_id=org_id,
                load_id=load_id,
                rule_code="missing_doc",
                severity=ValidationSeverity.WARNING,
                title="Missing document",
                description="A document is missing.",
                is_blocking=False,
                is_resolved=False,
            )
        )
    db_session.flush()

    result = ReviewQueueService(db_session).get_review_queue(
        organization_id=str(org_id), page=1, page_size=1
    )

    assert result["total"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 1
    assert len(result["items"]) == 1


def test_load_detail_keeps_packet_readiness_for_submission_gate(db_session) -> None:
    from app.api.v1.loads import _serialize_load

    org_id = uuid.uuid4()
    load_id = uuid.uuid4()
    customer_account_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    load = Load(
        id=load_id,
        organization_id=org_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        source_channel=Channel.MANUAL,
        status=LoadStatus.DELIVERED,
        processing_status=ProcessingStatus.COMPLETED,
        load_number="READY-1",
        currency_code="USD",
    )
    db_session.add(load)
    for document_type in (
        DocumentType.RATE_CONFIRMATION,
        DocumentType.PROOF_OF_DELIVERY,
        DocumentType.INVOICE,
    ):
        db_session.add(
            LoadDocument(
                organization_id=org_id,
                customer_account_id=customer_account_id,
                driver_id=driver_id,
                load_id=load_id,
                source_channel=Channel.MANUAL,
                document_type=document_type,
                original_filename=f"{document_type.value}.pdf",
                mime_type="application/pdf",
                file_size_bytes=123,
                storage_key=f"uploaded/{document_type.value}.pdf",
                file_hash_sha256=f"{document_type.value}-hash",
                received_at=datetime.now(timezone.utc),
                processing_status=ProcessingStatus.COMPLETED,
            )
        )
    db_session.flush()

    payload = _serialize_load(load, detailed=True, db=db_session)

    assert payload["packet_readiness"]["ready_to_submit"] is True
