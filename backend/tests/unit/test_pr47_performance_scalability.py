from __future__ import annotations

import pytest
from app.core.cache import CacheKey, TTLCache
from app.core.exceptions import ValidationError
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.load_document import LoadDocument
from app.domain.models.organization import Organization
from app.services.accounting import accounting_export_service as accounting_exports
from app.services.background.job_queue import JobStatus, job_queue
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService

ORG_ID = "00000000-0000-0000-0000-000000047001"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000047002"
CUSTOMER_ID = "00000000-0000-0000-0000-000000047011"


def _seed_document(db_session, *, storage_key: str = "text/sample.txt") -> LoadDocument:
    db_session.add(Organization(id=ORG_ID, name="PR47 Org", slug="pr47-org"))
    db_session.add(
        CustomerAccount(
            id=CUSTOMER_ID,
            organization_id=ORG_ID,
            account_name="PR47 Customer",
            account_code="PR47",
            status="active",
        )
    )
    db_session.flush()
    document = DocumentService(db_session).create_document(
        organization_id=ORG_ID,
        customer_account_id=CUSTOMER_ID,
        storage_key=storage_key,
        source_channel="manual",
        document_type="invoice",
        original_filename="sample.txt",
        mime_type="text/plain",
        file_size_bytes=42,
    )
    db_session.flush()
    return document


def test_cache_key_requires_organization_scope_for_operational_aggregates() -> None:
    cache: TTLCache[dict[str, str]] = TTLCache(max_entries=4)
    org_key = CacheKey(namespace="command_center", organization_id=ORG_ID)
    other_org_key = CacheKey(namespace="command_center", organization_id=OTHER_ORG_ID)

    cache.set(org_key, {"org": ORG_ID}, ttl_seconds=30)

    assert cache.get(org_key) == {"org": ORG_ID}
    assert cache.get(other_org_key) is None


def test_background_job_tracks_status_retries_and_idempotency() -> None:
    job_queue.reset()
    first = job_queue.enqueue(
        job_type="document_extraction",
        organization_id=ORG_ID,
        entity_type="document",
        entity_id="doc-1",
        idempotency_key="document_extraction:doc-1",
        max_attempts=1,
    )
    duplicate = job_queue.enqueue(
        job_type="document_extraction",
        organization_id=ORG_ID,
        entity_type="document",
        entity_id="doc-1",
        idempotency_key="document_extraction:doc-1",
        max_attempts=1,
    )

    assert duplicate.id == first.id

    job_queue.run(first.id, lambda: (_ for _ in ()).throw(RuntimeError("ocr failed")))
    failed = job_queue.get(first.id)

    assert failed is not None
    assert failed.status == JobStatus.FAILED
    assert failed.attempts == 1
    assert failed.last_error == "ocr failed"


def test_document_processing_status_supports_queued_and_failure_isolation(db_session) -> None:
    document = _seed_document(db_session)
    service = DocumentService(db_session)

    assert document.processing_status == ProcessingStatus.QUEUED

    updated = service.mark_processing(
        document_id=str(document.id),
        processing_status=ProcessingStatus.FAILED,
    )

    assert updated.processing_status == ProcessingStatus.FAILED


def test_accounting_export_safeguard_rejects_too_many_rows(db_session, monkeypatch) -> None:
    service = accounting_exports.AccountingExportService(db_session)
    monkeypatch.setattr(accounting_exports, "MAX_EXPORT_ROWS", 2)
    monkeypatch.setattr(
        service,
        "_base_rows",
        lambda *_args, **_kwargs: (
            {
                "invoice_number": str(i),
                "factoring_company": "",
                "funded_amount": "0.00",
                "partial_payment_amount": "0.00",
                "paid_date": "",
                "delivery_date": "",
                "invoice_date": "",
                "payment_status": "submitted",
                "reconciliation_status": "pending",
            }
            for i in range(3)
        ),
    )

    with pytest.raises(ValidationError) as exc:
        service.build_csv_export(ORG_ID, "invoices")

    assert exc.value.details["limit"] == 2


def test_private_document_file_response_is_not_publicly_cacheable(
    db_session, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    storage = StorageService()
    relative_path = storage.save_bytes(relative_path="text/private.txt", content=b"secret")

    response = storage.get_file(
        relative_path, download_filename="private.txt", media_type="text/plain"
    )

    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"

    get_settings.cache_clear()
