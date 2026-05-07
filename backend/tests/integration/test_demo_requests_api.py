from __future__ import annotations

from datetime import datetime, timezone

import pytest
from app.api.v1.demo_requests import (
    create_demo_request,
    list_demo_requests,
    update_demo_request_pipeline,
    update_demo_request_status,
)
from app.core.config import get_settings
from app.core.exceptions import RateLimitError, UnauthorizedError
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.demo_request import DemoRequest
from app.domain.models.notification import Notification
from app.schemas.demo_requests import (
    DemoRequestCreateRequest,
    DemoRequestPipelineUpdateRequest,
    DemoRequestStatusUpdateRequest,
)
from app.services.notifications.email_service import EmailService
from pydantic import ValidationError as PydanticValidationError


class _Client:
    host = "203.0.113.10"


class _Request:
    headers = {"user-agent": "pytest", "x-forwarded-for": "203.0.113.10"}
    client = _Client()


@pytest.fixture()
def demo_request_settings(monkeypatch):
    settings = get_settings()
    original = {
        "ops_notification_email": settings.ops_notification_email,
        "email_delivery_enabled": settings.email_delivery_enabled,
        "email_sending_enabled": settings.email_sending_enabled,
        "email_enabled": settings.email_enabled,
        "email_provider": settings.email_provider,
        "demo_request_rate_limit_max_per_ip": settings.demo_request_rate_limit_max_per_ip,
        "demo_request_rate_limit_window_seconds": settings.demo_request_rate_limit_window_seconds,
        "demo_request_duplicate_window_seconds": settings.demo_request_duplicate_window_seconds,
    }
    yield settings
    for key, value in original.items():
        monkeypatch.setattr(settings, key, value, raising=False)


def _payload(**overrides):
    data = {
        "full_name": "  Jane Doe  ",
        "email": "  JANE@EXAMPLE.COM ",
        "company": "  Acme Freight ",
        "phone": "  555-0100 ",
        "fleet_size": "  12 trucks ",
        "message": "  Need a walkthrough.  ",
    }
    data.update(overrides)
    return DemoRequestCreateRequest(**data)


def test_demo_request_valid_returns_201_and_saves(db_session):
    response = create_demo_request(payload=_payload(), db=db_session)
    assert response.data["status"] == "new"
    assert response.data["duplicate"] is False

    row = db_session.query(DemoRequest).one()
    assert row.full_name == "Jane Doe"
    assert row.company == "Acme Freight"
    assert row.email == "jane@example.com"
    assert row.phone == "555-0100"
    assert row.fleet_size == "12 trucks"
    assert row.message == "Need a walkthrough."
    assert row.status == "new"


def test_demo_request_creates_owner_and_ack_notifications_when_email_configured(
    db_session, demo_request_settings, monkeypatch
):
    monkeypatch.setattr(
        demo_request_settings, "ops_notification_email", "ops@example.com", raising=False
    )
    monkeypatch.setattr(demo_request_settings, "email_delivery_enabled", True, raising=False)
    monkeypatch.setattr(demo_request_settings, "email_provider", "none", raising=False)
    sent_messages = []

    def fake_send_message(self, *, to_email, subject, body_text, metadata=None):
        sent_messages.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body_text": body_text,
                "metadata": metadata or {},
            }
        )
        return {"status": "sent", "provider_message_id": f"test-{len(sent_messages)}"}

    monkeypatch.setattr(EmailService, "send_message", fake_send_message)

    response = create_demo_request(payload=_payload(), db=db_session)

    notifications = db_session.query(Notification).order_by(Notification.created_at.asc()).all()
    assert response.data["status"] == "new"
    assert [item.message_type for item in notifications] == [
        "demo_request_received",
        "demo_request_acknowledgement",
    ]
    assert {item.recipient for item in notifications} == {"ops@example.com", "jane@example.com"}
    assert all(item.status == NotificationStatus.SENT for item in notifications)
    assert "New Demo Request | Acme Freight" in notifications[0].subject
    assert "Status: new" in (notifications[0].body_text or "")
    assert "Fleet size: 12 trucks" in (notifications[0].body_text or "")
    assert "Freight Back Office OS" in (notifications[1].body_text or "")
    assert len(sent_messages) == 2


def test_demo_request_missing_email_config_still_saves_and_marks_skipped(db_session):
    response = create_demo_request(payload=_payload(), db=db_session)

    notifications = db_session.query(Notification).order_by(Notification.created_at.asc()).all()
    assert response.data["status"] == "new"
    assert db_session.query(DemoRequest).count() == 1
    assert [item.message_type for item in notifications] == [
        "demo_request_received",
        "demo_request_acknowledgement",
    ]
    assert all(item.status == NotificationStatus.SKIPPED for item in notifications)
    assert "recipient" in (notifications[0].error_message or "").lower()
    assert "email delivery" in (notifications[1].error_message or "").lower()


def test_demo_request_email_failure_does_not_break_submission(
    db_session, demo_request_settings, monkeypatch
):
    monkeypatch.setattr(
        demo_request_settings, "ops_notification_email", "ops@example.com", raising=False
    )
    monkeypatch.setattr(demo_request_settings, "email_delivery_enabled", True, raising=False)
    monkeypatch.setattr(demo_request_settings, "email_provider", "none", raising=False)

    def failing_send_message(self, *, to_email, subject, body_text, metadata=None):
        raise RuntimeError("smtp unavailable")

    monkeypatch.setattr(EmailService, "send_message", failing_send_message)

    response = create_demo_request(payload=_payload(), db=db_session)

    assert response.data["status"] == "new"
    assert db_session.query(DemoRequest).count() == 1
    notifications = db_session.query(Notification).all()
    assert len(notifications) == 2
    assert all(item.status == NotificationStatus.FAILED for item in notifications)


def test_demo_request_duplicate_payload_reuses_existing_lead_without_duplicate_notifications(
    db_session,
):
    first = create_demo_request(payload=_payload(), db=db_session)
    second = create_demo_request(payload=_payload(), db=db_session)

    assert second.data["id"] == first.data["id"]
    assert second.data["duplicate"] is True
    assert db_session.query(DemoRequest).count() == 1
    assert db_session.query(Notification).count() == 2


def test_demo_request_ip_rate_limit_blocks_obvious_flood(
    db_session, demo_request_settings, monkeypatch
):
    monkeypatch.setattr(
        demo_request_settings, "demo_request_rate_limit_max_per_ip", 1, raising=False
    )
    create_demo_request(
        payload=_payload(email="first@example.com", company="First Co"),
        request=_Request(),
        db=db_session,
    )

    with pytest.raises(RateLimitError):
        create_demo_request(
            payload=_payload(email="second@example.com", company="Second Co"),
            request=_Request(),
            db=db_session,
        )


def test_demo_request_list_allows_owner_admin_and_staff_roles(db_session):
    create_demo_request(payload=_payload(), db=db_session)

    for role in ["owner", "admin", "staff", "ops_manager", "ops_agent", "support_agent"]:
        response = list_demo_requests(
            page=1,
            page_size=50,
            token_payload={"role": role},
            db=db_session,
        )
        assert response.meta["total"] == 1
        assert response.data[0]["email"] == "jane@example.com"


def test_demo_request_list_rejects_driver(db_session):
    create_demo_request(payload=_payload(), db=db_session)

    with pytest.raises(UnauthorizedError):
        list_demo_requests(
            page=1,
            page_size=50,
            token_payload={"role": "driver"},
            db=db_session,
        )


def test_demo_request_list_supports_search_filter_and_metrics(db_session):
    create_demo_request(
        payload=_payload(email="jane@example.com", company="Acme Freight"), db=db_session
    )
    second = create_demo_request(
        payload=_payload(
            full_name="Sam Carrier",
            email="sam@example.com",
            company="Bluebird Logistics",
            phone="555-9999",
        ),
        db=db_session,
    )
    update_demo_request_status(
        demo_request_id=second.data["id"],
        payload=DemoRequestStatusUpdateRequest(status="contacted"),
        token_payload={"role": "owner"},
        db=db_session,
    )

    response = list_demo_requests(
        status_filter="contacted",
        search="bluebird",
        page=1,
        page_size=50,
        token_payload={"role": "ops_agent"},
        db=db_session,
    )

    assert response.meta["total"] == 1
    assert response.data[0]["company"] == "Bluebird Logistics"
    assert response.meta["metrics"]["new"] == 1
    assert response.meta["metrics"]["contacted"] == 1


def test_demo_request_pipeline_update_persists_notes_and_follow_up(db_session):
    created = create_demo_request(payload=_payload(), db=db_session)
    follow_up = datetime(2026, 5, 8, 15, 30, tzinfo=timezone.utc)

    response = update_demo_request_pipeline(
        demo_request_id=created.data["id"],
        payload=DemoRequestPipelineUpdateRequest(
            status="scheduled",
            notes="Call booked with owner.",
            next_follow_up_at=follow_up,
        ),
        token_payload={"role": "support_agent"},
        db=db_session,
    )

    assert response.data["status"] == "scheduled"
    assert response.data["notes"] == "Call booked with owner."
    assert response.data["next_follow_up_at"].startswith("2026-05-08T15:30:00")

    row = db_session.get(DemoRequest, created.data["id"])
    assert row is not None
    assert row.notes == "Call booked with owner."
    assert row.next_follow_up_at is not None


def test_demo_request_closed_status_is_normalized_to_lost(db_session):
    created = create_demo_request(payload=_payload(), db=db_session)
    response = update_demo_request_status(
        demo_request_id=created.data["id"],
        payload=DemoRequestStatusUpdateRequest(status="closed"),
        token_payload={"role": "admin"},
        db=db_session,
    )

    assert response.data["status"] == "lost"
    assert db_session.get(DemoRequest, created.data["id"]).status == "lost"


def test_demo_request_status_update_for_staff(db_session):
    created = create_demo_request(payload=_payload(), db=db_session)
    response = update_demo_request_status(
        demo_request_id=created.data["id"],
        payload=DemoRequestStatusUpdateRequest(status="scheduled"),
        token_payload={"role": "admin", "organization_id": "00000000-0000-0000-0000-000000000001"},
        db=db_session,
    )

    assert response.data["status"] == "scheduled"
    list_response = list_demo_requests(
        status_filter="scheduled",
        page=1,
        page_size=50,
        token_payload={"role": "admin", "organization_id": "00000000-0000-0000-0000-000000000001"},
        db=db_session,
    )
    assert list_response.meta["total"] == 1
    assert list_response.data[0]["status"] == "scheduled"


def test_demo_request_status_update_rejects_driver(db_session):
    created = create_demo_request(payload=_payload(), db=db_session)
    with pytest.raises(UnauthorizedError):
        update_demo_request_status(
            demo_request_id=created.data["id"],
            payload=DemoRequestStatusUpdateRequest(status="contacted"),
            token_payload={"role": "driver"},
            db=db_session,
        )


def test_demo_request_missing_full_name_returns_422():
    with pytest.raises(PydanticValidationError):
        DemoRequestCreateRequest(email="a@b.com", company="Acme")


def test_demo_request_invalid_email_returns_422():
    with pytest.raises(PydanticValidationError):
        DemoRequestCreateRequest(full_name="Jane", email="invalid", company="Acme")


def test_demo_request_missing_company_returns_422():
    with pytest.raises(PydanticValidationError):
        DemoRequestCreateRequest(full_name="Jane", email="jane@example.com")


def test_demo_request_forbids_extra_fields():
    with pytest.raises(PydanticValidationError):
        DemoRequestCreateRequest(
            full_name="Jane", email="jane@example.com", company="Acme", unexpected="x"
        )
