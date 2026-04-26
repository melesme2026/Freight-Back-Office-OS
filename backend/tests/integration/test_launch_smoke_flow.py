from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from starlette.datastructures import UploadFile

from app.api.v1.documents import upload_driver_document
from app.api.v1.follow_ups import generate_followups_for_load
from app.api.v1.load_payment_reconciliation import (
    MarkPaidRequest,
    MarkPartialRequest,
    mark_paid,
    mark_partial_payment,
)
from app.api.v1.loads import (
    SubmissionPacketCreateRequest,
    SubmissionPacketMarkSentRequest,
    _authorize_load_access,
    create_submission_packet,
    download_load_invoice,
    download_submission_packet_zip,
    mark_submission_packet_sent,
)
from app.api.v1.reports import _authorize_reports_read, get_money_dashboard
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.domain.models.broker import Broker
from app.domain.models.carrier_profile import CarrierProfile
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.organization import Organization
from app.domain.models.driver import Driver
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService


def _staff_payload(org_id: str) -> dict[str, str]:
    return {"organization_id": org_id, "role": "admin", "staff_user_id": "00000000-0000-0000-0000-000000001111"}


def _driver_payload(org_id: str, driver_id: str) -> dict[str, str]:
    return {"organization_id": org_id, "role": "driver", "driver_id": driver_id, "sub": driver_id}


def test_launch_smoke_owner_admin_and_driver_flow(db_session):
    org_id = "00000000-0000-0000-0000-000000040001"
    customer_id = "00000000-0000-0000-0000-000000040011"
    broker_id = "00000000-0000-0000-0000-000000040012"
    driver_id = "00000000-0000-0000-0000-000000040013"

    db_session.add(Organization(id=org_id, name="Smoke Org", slug="smoke-org"))
    db_session.add(
        CarrierProfile(
            organization_id=org_id,
            legal_name="Demo Carrier LLC",
            mc_number="MC111111",
            dot_number="DOT111111",
            address_line1="100 Freight Way",
            city="Dallas",
            state="TX",
            zip="75001",
            phone="5551000",
            email="carrier@example.com",
            remit_to_name="Demo Carrier LLC",
            remit_to_address="100 Freight Way, Dallas TX 75001",
        )
    )
    db_session.add(CustomerAccount(id=customer_id, organization_id=org_id, account_name="Demo Customer", account_code="DEMO", status="active"))
    db_session.add(Broker(id=broker_id, organization_id=org_id, name="Demo Broker", mc_number="MC999111", email="broker@example.com", payment_terms_days=30))
    db_session.add(Driver(id=driver_id, organization_id=org_id, customer_account_id=customer_id, full_name="Driver Smoke", phone="5551234", email="driver-smoke@example.com", is_active=True))
    db_session.flush()

    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        broker_id=broker_id,
        load_number="SMK-001",
        pickup_location="Chicago, IL",
        delivery_location="Atlanta, GA",
    )

    storage_root = Path("data/sandbox/uploaded-docs")
    storage_root.mkdir(parents=True, exist_ok=True)

    docs = DocumentService(db_session)
    for idx, doc_type in enumerate(["rate_confirmation", "bill_of_lading", "proof_of_delivery"], start=1):
        storage_key = f"uploads/smoke-{doc_type}-{idx}.pdf"
        full_path = storage_root / storage_key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(b"smoke-doc")
        docs.create_document(
            organization_id=org_id,
            customer_account_id=customer_id,
            storage_key=f"uploads/smoke-{doc_type}-{idx}.pdf",
            source_channel="web",
            driver_id=driver_id,
            load_id=str(load.id),
            document_type=doc_type,
            original_filename=f"{doc_type}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
        )

    invoice_resp = download_load_invoice(load_id=load.id, token_payload=_staff_payload(org_id), db=db_session)
    assert invoice_resp.media_type == "application/pdf"

    invoice_docs, _ = docs.list_documents(organization_id=org_id, load_id=str(load.id), document_type="invoice", page=1, page_size=20)
    assert len(invoice_docs) >= 1

    packet_resp = create_submission_packet(load_id=load.id, payload=SubmissionPacketCreateRequest(notes="launch smoke"), token_payload=_staff_payload(org_id), db=db_session)
    packet_id = packet_resp.data["id"]

    zip_resp = download_submission_packet_zip(load_id=load.id, packet_id=packet_id, token_payload=_staff_payload(org_id), db=db_session)
    assert zip_resp.media_type == "application/zip"

    sent_resp = mark_submission_packet_sent(
        load_id=load.id,
        packet_id=packet_id,
        payload=SubmissionPacketMarkSentRequest(destination_type="broker", destination_name="Demo Broker", destination_email="broker@example.com", notes="emailed"),
        token_payload=_staff_payload(org_id),
        db=db_session,
    )
    assert sent_resp.data["status"] == "sent"

    partial = mark_partial_payment(
        load_id=str(load.id),
        payload=MarkPartialRequest(amount="400"),
        db=db_session,
        token_payload=_staff_payload(org_id),
    )
    assert partial.data["payment_status"] == "partially_paid"

    paid = mark_paid(
        load_id=str(load.id),
        payload=MarkPaidRequest(amount="1000"),
        db=db_session,
        token_payload=_staff_payload(org_id),
    )
    assert paid.data["amount_received"] == "1000"

    followups = generate_followups_for_load(load_id=str(load.id), db=db_session, token_payload=_staff_payload(org_id))
    assert isinstance(followups.data, list)

    dashboard = get_money_dashboard(token_payload=_staff_payload(org_id), db=db_session)
    assert "summary" in dashboard.data

    driver_docs = asyncio.run(
        upload_driver_document(
            organization_id=org_id,
            token_payload=_driver_payload(org_id, driver_id),
            file=UploadFile(filename="driver-pod.pdf", file=BytesIO(b"driver-pod"), headers={"content-type": "application/pdf"}),
            document_type="proof_of_delivery",
            load_id=load.id,
            db=db_session,
        )
    )
    assert driver_docs.meta["driver_upload"] is True

    # Driver sees own load and cannot see others
    own_items, own_total = LoadService(db_session).list_loads(organization_id=org_id, driver_id=driver_id, page=1, page_size=20)
    assert own_total == 1
    assert len(own_items) == 1

    other_driver_id = "00000000-0000-0000-0000-000000040099"
    db_session.add(Driver(id=other_driver_id, organization_id=org_id, customer_account_id=customer_id, full_name="Other Driver", phone="5559999", email=None, is_active=True))
    other_load = LoadService(db_session).create_load(organization_id=org_id, customer_account_id=customer_id, driver_id=other_driver_id, load_number="SMK-002", pickup_location="LA", delivery_location="SF")

    with pytest.raises(UnauthorizedError):
        _authorize_load_access(item=other_load, token_payload=_driver_payload(org_id, driver_id))

    with pytest.raises(ForbiddenError):
        _authorize_reports_read(_driver_payload(org_id, driver_id))
