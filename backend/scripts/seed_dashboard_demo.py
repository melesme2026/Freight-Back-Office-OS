from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.database import get_session_factory, init_db
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.domain.models.validation_issue import ValidationIssue
from app.repositories.broker_repo import BrokerRepository


ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
CUSTOMER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
DRIVER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
STAFF_USER_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")

LOAD_1_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
LOAD_2_ID = uuid.UUID("60000000-0000-0000-0000-000000000002")
LOAD_3_ID = uuid.UUID("60000000-0000-0000-0000-000000000003")

DOC_1_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
DOC_2_ID = uuid.UUID("70000000-0000-0000-0000-000000000002")
DOC_3_ID = uuid.UUID("70000000-0000-0000-0000-000000000003")

ISSUE_1_ID = uuid.UUID("80000000-0000-0000-0000-000000000001")
ISSUE_2_ID = uuid.UUID("80000000-0000-0000-0000-000000000002")
ISSUE_3_ID = uuid.UUID("80000000-0000-0000-0000-000000000003")


def ensure_required_seed_entities(db):
    organization = db.get(Organization, ORG_ID)
    if organization is None:
        raise RuntimeError("Organization seed missing. Run `python backend\\scripts\\seed.py` first.")

    customer = db.get(CustomerAccount, CUSTOMER_ID)
    if customer is None:
        raise RuntimeError("Customer account seed missing. Run `python backend\\scripts\\seed.py` first.")

    driver = db.get(Driver, DRIVER_ID)
    if driver is None:
        raise RuntimeError("Driver seed missing. Run `python backend\\scripts\\seed.py` first.")

    staff_user = db.get(StaffUser, STAFF_USER_ID)
    if staff_user is None:
        raise RuntimeError("Staff user seed missing. Run `python backend\\scripts\\seed.py` first.")

    broker_repo = BrokerRepository(db)
    brokers, _ = broker_repo.list(organization_id=ORG_ID, page=1, page_size=1)
    broker_id = brokers[0].id if brokers else None

    return customer, driver, staff_user, broker_id


def upsert_loads(db, customer: CustomerAccount, driver: Driver, broker_id: uuid.UUID | None) -> None:
    today = date.today()
    now = datetime.now(UTC)

    demo_loads = [
        {
            "id": LOAD_1_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "broker_id": broker_id,
            "source_channel": "manual",
            "status": "needs_review",
            "processing_status": "in_progress",
            "load_number": "FBOS-DEMO-1001",
            "rate_confirmation_number": "RC-1001",
            "bol_number": "BOL-1001",
            "invoice_number": None,
            "broker_name_raw": "Global Freight Brokers",
            "broker_email_raw": "lisa@globalfreight.com",
            "pickup_date": today - timedelta(days=1),
            "delivery_date": today + timedelta(days=1),
            "pickup_location": "Detroit, MI",
            "delivery_location": "Chicago, IL",
            "gross_amount": Decimal("1850.00"),
            "currency_code": "USD",
            "documents_complete": False,
            "has_ratecon": True,
            "has_bol": True,
            "has_invoice": False,
            "extraction_confidence_avg": Decimal("0.9125"),
            "last_reviewed_by": None,
            "last_reviewed_at": None,
            "submitted_at": None,
            "funded_at": None,
            "paid_at": None,
            "notes": "Demo load requiring review",
        },
        {
            "id": LOAD_2_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "broker_id": broker_id,
            "source_channel": "manual",
            "status": "validated",
            "processing_status": "completed",
            "load_number": "FBOS-DEMO-1002",
            "rate_confirmation_number": "RC-1002",
            "bol_number": "BOL-1002",
            "invoice_number": "INV-1002",
            "broker_name_raw": "Summit Logistics Group",
            "broker_email_raw": "david@summitlogistics.com",
            "pickup_date": today - timedelta(days=3),
            "delivery_date": today - timedelta(days=1),
            "pickup_location": "Cleveland, OH",
            "delivery_location": "Columbus, OH",
            "gross_amount": Decimal("1425.50"),
            "currency_code": "USD",
            "documents_complete": True,
            "has_ratecon": True,
            "has_bol": True,
            "has_invoice": True,
            "extraction_confidence_avg": Decimal("0.9810"),
            "last_reviewed_by": STAFF_USER_ID,
            "last_reviewed_at": now - timedelta(hours=10),
            "submitted_at": None,
            "funded_at": None,
            "paid_at": None,
            "notes": "Demo validated load",
        },
        {
            "id": LOAD_3_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "broker_id": broker_id,
            "source_channel": "manual",
            "status": "paid",
            "processing_status": "completed",
            "load_number": "FBOS-DEMO-1003",
            "rate_confirmation_number": "RC-1003",
            "bol_number": "BOL-1003",
            "invoice_number": "INV-1003",
            "broker_name_raw": "Global Freight Brokers",
            "broker_email_raw": "lisa@globalfreight.com",
            "pickup_date": today - timedelta(days=6),
            "delivery_date": today - timedelta(days=4),
            "pickup_location": "Indianapolis, IN",
            "delivery_location": "Louisville, KY",
            "gross_amount": Decimal("2100.75"),
            "currency_code": "USD",
            "documents_complete": True,
            "has_ratecon": True,
            "has_bol": True,
            "has_invoice": True,
            "extraction_confidence_avg": Decimal("0.9550"),
            "last_reviewed_by": STAFF_USER_ID,
            "last_reviewed_at": now - timedelta(days=2),
            "submitted_at": now - timedelta(days=3),
            "funded_at": now - timedelta(days=2),
            "paid_at": now - timedelta(days=1),
            "notes": "Demo paid load",
        },
    ]

    try:
        for item in demo_loads:
            existing = db.get(Load, item["id"])
            if existing is None:
                db.add(Load(**item))
            else:
                for key, value in item.items():
                    setattr(existing, key, value)
        db.commit()
    except Exception:
        db.rollback()
        raise


def upsert_documents(db, customer: CustomerAccount, driver: Driver, staff_user: StaffUser) -> None:
    now = datetime.now(UTC)

    demo_documents = [
        {
            "id": DOC_1_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "load_id": LOAD_1_ID,
            "source_channel": "manual",
            "document_type": "bill_of_lading",
            "original_filename": "fbos-demo-bol-1001.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 148224,
            "storage_bucket": "local-dev",
            "storage_key": "demo/fbos-demo-bol-1001.pdf",
            "file_hash_sha256": "a" * 64,
            "page_count": 2,
            "processing_status": "pending",
            "classification_confidence": 0.92,
            "ocr_completed_at": None,
            "received_at": now - timedelta(hours=12),
            "uploaded_by_staff_user_id": staff_user.id,
        },
        {
            "id": DOC_2_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "load_id": LOAD_2_ID,
            "source_channel": "manual",
            "document_type": "proof_of_delivery",
            "original_filename": "fbos-demo-pod-1002.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 182442,
            "storage_bucket": "local-dev",
            "storage_key": "demo/fbos-demo-pod-1002.pdf",
            "file_hash_sha256": "b" * 64,
            "page_count": 1,
            "processing_status": "completed",
            "classification_confidence": 0.98,
            "ocr_completed_at": now - timedelta(hours=8),
            "received_at": now - timedelta(hours=9),
            "uploaded_by_staff_user_id": staff_user.id,
        },
        {
            "id": DOC_3_ID,
            "organization_id": ORG_ID,
            "customer_account_id": customer.id,
            "driver_id": driver.id,
            "load_id": LOAD_3_ID,
            "source_channel": "manual",
            "document_type": "rate_confirmation",
            "original_filename": "fbos-demo-ratecon-1003.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 205901,
            "storage_bucket": "local-dev",
            "storage_key": "demo/fbos-demo-ratecon-1003.pdf",
            "file_hash_sha256": "c" * 64,
            "page_count": 3,
            "processing_status": "in_progress",
            "classification_confidence": 0.87,
            "ocr_completed_at": None,
            "received_at": now - timedelta(hours=4),
            "uploaded_by_staff_user_id": staff_user.id,
        },
    ]

    try:
        for item in demo_documents:
            existing = db.get(LoadDocument, item["id"])
            if existing is None:
                db.add(LoadDocument(**item))
            else:
                for key, value in item.items():
                    setattr(existing, key, value)
        db.commit()
    except Exception:
        db.rollback()
        raise


def upsert_validation_issues(db, staff_user: StaffUser) -> None:
    now = datetime.now(UTC)

    demo_issues = [
        {
            "id": ISSUE_1_ID,
            "organization_id": ORG_ID,
            "load_id": LOAD_1_ID,
            "document_id": DOC_1_ID,
            "rule_code": "missing_delivery_signature",
            "severity": "critical",
            "title": "Missing delivery signature",
            "description": "Proof of delivery is missing a required consignee signature.",
            "is_blocking": True,
            "is_resolved": False,
            "resolved_by_staff_user_id": None,
            "resolved_at": None,
            "resolution_notes": None,
        },
        {
            "id": ISSUE_2_ID,
            "organization_id": ORG_ID,
            "load_id": LOAD_1_ID,
            "document_id": DOC_1_ID,
            "rule_code": "rate_mismatch_warning",
            "severity": "warning",
            "title": "Rate mismatch warning",
            "description": "Carrier charge differs from expected contracted amount.",
            "is_blocking": False,
            "is_resolved": False,
            "resolved_by_staff_user_id": None,
            "resolved_at": None,
            "resolution_notes": None,
        },
        {
            "id": ISSUE_3_ID,
            "organization_id": ORG_ID,
            "load_id": LOAD_2_ID,
            "document_id": DOC_2_ID,
            "rule_code": "resolved_doc_quality",
            "severity": "critical",
            "title": "Resolved scan quality issue",
            "description": "Historical critical issue retained for realism but already resolved.",
            "is_blocking": False,
            "is_resolved": True,
            "resolved_by_staff_user_id": staff_user.id,
            "resolved_at": now - timedelta(hours=6),
            "resolution_notes": "Resubmitted clean scan and confirmed fields.",
        },
    ]

    try:
        for item in demo_issues:
            existing = db.get(ValidationIssue, item["id"])
            if existing is None:
                db.add(ValidationIssue(**item))
            else:
                for key, value in item.items():
                    setattr(existing, key, value)
        db.commit()
    except Exception:
        db.rollback()
        raise


def main() -> None:
    init_db(import_models=True)

    session_factory = get_session_factory()
    db = session_factory()
    try:
        customer, driver, staff_user, broker_id = ensure_required_seed_entities(db)
        upsert_loads(db, customer, driver, broker_id)
        upsert_documents(db, customer, driver, staff_user)
        upsert_validation_issues(db, staff_user)

        print("✅ Dashboard demo data ready")
        print("   Loads: 3")
        print("   Documents: 3")
        print("   Validation issues: 3")
        print("   Expected dashboard direction:")
        print("   - Loads in progress > 0")
        print("   - Needs review > 0")
        print("   - Pending documents > 0")
        print("   - Critical issues > 0")
    finally:
        db.close()


if __name__ == "__main__":
    main()