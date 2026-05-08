from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.core.exceptions import UnauthorizedError, ValidationError
from app.domain.models.audit_log import AuditLog
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.load_document import LoadDocument
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.services.accounting import accounting_export_service as export_module
from app.services.accounting.accounting_export_service import AccountingExportService
from app.services.audit.activity_service import ActivityService
from app.services.audit.audit_service import AuditService
from app.services.documents.storage_service import StorageService
from app.services.organizations.quota_service import OrganizationQuotaService
from app.services.storage.cleanup_service import StorageCleanupService

ORG_ID = "00000000-0000-0000-0000-000000042001"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000042002"
CUSTOMER_ID = "00000000-0000-0000-0000-000000042101"
STAFF_ID = "00000000-0000-0000-0000-000000042201"
DOC_ID = "00000000-0000-0000-0000-000000042301"
OTHER_DOC_ID = "00000000-0000-0000-0000-000000042302"


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _seed_orgs(db_session) -> None:
    db_session.add(Organization(id=_uuid(ORG_ID), name="PR42 Org", slug="pr42-org"))
    db_session.add(Organization(id=_uuid(OTHER_ORG_ID), name="Other Org", slug="pr42-other"))
    db_session.add(
        CustomerAccount(
            id=_uuid(CUSTOMER_ID),
            organization_id=_uuid(ORG_ID),
            account_name="PR42 Customer",
            account_code="PR42",
            status="active",
        )
    )
    db_session.add(
        StaffUser(
            id=_uuid(STAFF_ID),
            organization_id=_uuid(ORG_ID),
            email="pr42@example.com",
            full_name="PR42 Admin",
            password_hash="hash",
            role="admin",
            is_active=True,
        )
    )
    db_session.flush()


def _seed_document(db_session, *, storage_key: str = "pdfs/referenced.pdf") -> None:
    _seed_orgs(db_session)
    db_session.add(
        LoadDocument(
            id=_uuid(DOC_ID),
            organization_id=_uuid(ORG_ID),
            customer_account_id=_uuid(CUSTOMER_ID),
            source_channel="manual",
            document_type="invoice",
            original_filename="invoice.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            storage_key=storage_key,
            file_hash_sha256="a" * 64,
            processing_status="pending",
            received_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()


def test_activity_listing_is_organization_scoped_and_sanitized(db_session):
    _seed_orgs(db_session)
    service = AuditService(db_session)
    service.log_event(
        organization_id=_uuid(ORG_ID),
        entity_type="document",
        entity_id=_uuid(DOC_ID),
        action="document.uploaded",
        actor_id=_uuid(STAFF_ID),
        actor_type="staff_user",
        metadata_json={"filename": "invoice.pdf", "stripe_secret": "hidden"},
    )
    service.log_event(
        organization_id=_uuid(OTHER_ORG_ID),
        entity_type="document",
        entity_id=OTHER_DOC_ID,
        action="document.uploaded",
        metadata_json={"filename": "other.pdf"},
    )

    items, meta = ActivityService(db_session).list_recent_activity(
        organization_id=_uuid(ORG_ID),
        token_payload={"organization_id": ORG_ID},
        limit=10,
    )

    assert meta["total_count"] == 1
    assert [item["organization_id"] for item in items] == [ORG_ID]
    assert items[0]["metadata"] == {"filename": "invoice.pdf"}

    with pytest.raises(UnauthorizedError):
        ActivityService(db_session).list_recent_activity(
            organization_id=_uuid(OTHER_ORG_ID),
            token_payload={"organization_id": ORG_ID},
        )


def test_quota_helpers_warn_first_without_hard_lockout(db_session):
    _seed_document(db_session)
    service = OrganizationQuotaService(
        db_session,
        quotas={"storage_bytes": 1000, "document_count": 1},
    )

    decision = service.can_upload_document(
        organization_id=_uuid(ORG_ID),
        incoming_size_bytes=100,
        enforce=False,
    )

    assert decision.allowed is True
    assert decision.warning is True
    assert "quota" in (decision.reason or "").lower()

    enforced = service.can_upload_document(
        organization_id=_uuid(ORG_ID),
        incoming_size_bytes=100,
        enforce=True,
    )
    assert enforced.allowed is False


def test_storage_cleanup_dry_run_only_reports_unreferenced_old_managed_files(db_session, tmp_path):
    _seed_document(db_session, storage_key="pdfs/referenced.pdf")
    storage = StorageService()
    storage.root = tmp_path.resolve()
    referenced = tmp_path / "pdfs" / "referenced.pdf"
    orphaned = tmp_path / "pdfs" / "orphaned.pdf"
    temp_file = tmp_path / "tmp" / "old.tmp"
    ignored = tmp_path / "manual" / "keep.txt"
    for path in (referenced, orphaned, temp_file, ignored):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=45)).timestamp()
    for path in (referenced, orphaned, temp_file, ignored):
        path.touch()
        path.chmod(0o644)
        import os

        os.utime(path, (old_timestamp, old_timestamp))

    result = StorageCleanupService(db_session, storage=storage).dry_run(retention_days=30)
    candidate_paths = {item["relative_path"] for item in result["candidates"]}

    assert result["dry_run"] is True
    assert "pdfs/orphaned.pdf" in candidate_paths
    assert "tmp/old.tmp" in candidate_paths
    assert "pdfs/referenced.pdf" not in candidate_paths
    assert "manual/keep.txt" not in candidate_paths
    assert orphaned.exists()
    assert temp_file.exists()


def test_accounting_export_row_limit_is_enforced(db_session, monkeypatch):
    _seed_orgs(db_session)
    service = AccountingExportService(db_session)
    monkeypatch.setattr(export_module, "MAX_EXPORT_ROWS", 1)
    monkeypatch.setattr(
        AccountingExportService,
        "_base_rows",
        lambda self, org_id, mapping: [
            {"invoice_date": "", "delivery_date": "", "paid_date": "", "payment_status": "paid", "reconciliation_status": "reconciled"},
            {"invoice_date": "", "delivery_date": "", "paid_date": "", "payment_status": "paid", "reconciliation_status": "reconciled"},
        ],
    )

    with pytest.raises(ValidationError):
        service.build_csv_export(ORG_ID, "invoices")
