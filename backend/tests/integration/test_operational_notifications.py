from __future__ import annotations

import asyncio
from io import BytesIO

from starlette.datastructures import UploadFile

from app.api.v1.demo_requests import create_demo_request
from app.api.v1.documents import upload_document, upload_driver_document
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.notification import Notification
from app.domain.models.organization import Organization
from app.schemas.demo_requests import DemoRequestCreateRequest
from app.services.loads.load_service import LoadService
from app.services.notifications.email_service import EmailService
from app.services.notifications.operational_notification_service import OperationalNotificationService


def _seed_upload_base(db_session, *, driver_email: str | None = "driver@example.com"):
    org_id = "00000000-0000-0000-0000-000000088001"
    customer_id = "00000000-0000-0000-0000-000000088011"
    driver_id = "00000000-0000-0000-0000-000000088021"
    db_session.add(Organization(id=org_id, name="Notify Org", slug="notify-org"))
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name="Notify Customer",
            account_code="NOTIFY",
            status="active",
        )
    )
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name="Notify Driver",
            phone="5558800",
            email=driver_email,
            is_active=True,
        )
    )
    db_session.flush()
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="NOTIFY-001",
    )
    return org_id, customer_id, driver_id, str(load.id)


def test_demo_request_creates_skipped_notification_when_email_config_missing(db_session):
    payload = DemoRequestCreateRequest(
        full_name="Jane Notify",
        email="jane.notify@example.com",
        company="Notify Co",
        message="Please call.",
    )

    response = create_demo_request(payload=payload, db=db_session)

    notification = db_session.query(Notification).one()
    assert response.data["status"] == "received"
    assert notification.message_type == "demo_request_received"
    assert str(notification.demo_request_id) == response.data["id"]
    assert notification.status == NotificationStatus.SKIPPED
    assert "recipient" in (notification.error_message or "").lower()


def test_owner_document_upload_creates_notification(db_session):
    org_id, customer_id, driver_id, load_id = _seed_upload_base(db_session)

    asyncio.run(
        upload_document(
            organization_id=org_id,
            token_payload={
                "organization_id": org_id,
                "role": "owner",
                "sub": "00000000-0000-0000-0000-000000009999",
            },
            customer_account_id=customer_id,
            source_channel="manual",
            file=UploadFile(
                filename="ratecon.pdf",
                file=BytesIO(b"ratecon-one"),
                headers={"content-type": "application/pdf"},
            ),
            driver_id=driver_id,
            load_id=load_id,
            document_type="rate_confirmation",
            uploaded_by_staff_user_id=None,
            page_count=None,
            replace=None,
            db=db_session,
        )
    )

    notification = db_session.query(Notification).filter_by(message_type="document_uploaded").one()
    assert str(notification.load_id) == load_id
    assert notification.document_id is not None
    assert notification.status == NotificationStatus.SKIPPED


def test_driver_document_upload_creates_ops_and_driver_confirmation_notifications(db_session):
    org_id, _, driver_id, load_id = _seed_upload_base(db_session)

    asyncio.run(
        upload_driver_document(
            organization_id=org_id,
            token_payload={
                "organization_id": org_id,
                "role": "driver",
                "driver_id": driver_id,
                "sub": driver_id,
            },
            file=UploadFile(
                filename="pod.pdf",
                file=BytesIO(b"pod-one"),
                headers={"content-type": "application/pdf"},
            ),
            document_type="proof_of_delivery",
            load_id=load_id,
            replace=None,
            db=db_session,
        )
    )

    notifications = db_session.query(Notification).order_by(Notification.message_type).all()
    assert {item.message_type for item in notifications} == {
        "document_uploaded",
        "driver_upload_confirmation",
    }
    driver_confirmation = next(
        item for item in notifications if item.message_type == "driver_upload_confirmation"
    )
    assert driver_confirmation.recipient == "driver@example.com"
    assert driver_confirmation.status == NotificationStatus.SKIPPED


def test_email_failure_marks_notification_failed_without_breaking_action(db_session, monkeypatch):
    org_id, customer_id, driver_id, load_id = _seed_upload_base(db_session)

    monkeypatch.setattr(OperationalNotificationService, "_ops_recipient", lambda self: "ops@example.com")
    monkeypatch.setattr(OperationalNotificationService, "_email_configured", lambda self: True)

    def fail_send(self, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(EmailService, "send_message", fail_send)

    response = asyncio.run(
        upload_document(
            organization_id=org_id,
            token_payload={
                "organization_id": org_id,
                "role": "owner",
                "sub": "00000000-0000-0000-0000-000000009999",
            },
            customer_account_id=customer_id,
            source_channel="manual",
            file=UploadFile(
                filename="invoice.pdf",
                file=BytesIO(b"invoice-one"),
                headers={"content-type": "application/pdf"},
            ),
            driver_id=driver_id,
            load_id=load_id,
            document_type="invoice",
            uploaded_by_staff_user_id=None,
            page_count=None,
            replace=None,
            db=db_session,
        )
    )

    notification = db_session.query(Notification).one()
    assert response.meta["uploaded"] is True
    assert notification.status == NotificationStatus.FAILED
    assert notification.error_message == "Email delivery failed."
