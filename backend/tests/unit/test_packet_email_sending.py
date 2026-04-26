from __future__ import annotations

import pytest

from app.api.v1.loads import SubmissionPacketSendEmailRequest, send_submission_packet_email
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError, ValidationError
from app.domain.enums.document_type import DocumentType
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.loads.load_service import LoadService
from app.services.loads.submission_packet_service import SubmissionPacketService


def _seed_packet(db_session, *, organization_id: str):
    load = LoadService(db_session).create_load(
        organization_id=organization_id,
        customer_account_id="00000000-0000-0000-0000-000000008002",
        driver_id="00000000-0000-0000-0000-000000008003",
        load_number="LD-EMAIL-001",
        broker_email_raw="billing@broker.test",
        broker_name_raw="Broker AP",
    )
    doc_service = DocumentService(db_session)
    required = [
        DocumentType.RATE_CONFIRMATION,
        DocumentType.PROOF_OF_DELIVERY,
        DocumentType.INVOICE,
        DocumentType.BILL_OF_LADING,
    ]
    for idx, doc_type in enumerate(required, start=1):
        document = doc_service.create_document(
            organization_id=organization_id,
            customer_account_id="00000000-0000-0000-0000-000000008002",
            driver_id="00000000-0000-0000-0000-000000008003",
            load_id=str(load.id),
            source_channel="manual",
            document_type=doc_type,
            storage_key=f"uploads/packet-email-{idx}.pdf",
            original_filename=f"packet-email-{idx}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1000 + idx,
        )
        StorageService().save_bytes(relative_path=document.storage_key, content=f"{doc_type.value}-file".encode("utf-8"), overwrite=True)

    packet = SubmissionPacketService(db_session).create_packet_from_load(str(load.id), organization_id, None)
    return load, packet


def _token(org_id: str, role: str = "ops") -> dict[str, str]:
    return {
        "organization_id": org_id,
        "role": role,
        "staff_user_id": "00000000-0000-0000-0000-000000008099",
    }


def test_send_email_disabled_returns_clear_error_and_no_sent_status(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000008001"
    load, packet = _seed_packet(db_session, organization_id=org_id)

    with pytest.raises(ConflictError) as exc:
        send_submission_packet_email(
            load_id=load.id,
            packet_id=packet.id,
            payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
            token_payload=_token(org_id),
            db=db_session,
        )

    assert "Email sending is disabled" in exc.value.message
    refreshed = SubmissionPacketService(db_session).get_packet(str(packet.id), str(load.id), org_id)
    assert refreshed.status == "ready"
    event_types = [event.event_type for event in refreshed.events]
    assert "packet_email_send_attempt" in event_types
    assert "packet_email_failed" in event_types


def test_smtp_config_missing_returns_clear_error(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    org_id = "00000000-0000-0000-0000-000000008011"
    load, packet = _seed_packet(db_session, organization_id=org_id)

    def _mock_send(self, **_: object):
        return {
            "provider": "smtp",
            "accepted": False,
            "provider_message_id": None,
            "error_message": "SMTP_HOST is required for SMTP packet email sending.",
        }

    monkeypatch.setattr("app.api.v1.loads.PacketEmailService.send_email_with_attachments", _mock_send)

    with pytest.raises(ValidationError) as exc:
        send_submission_packet_email(
            load_id=load.id,
            packet_id=packet.id,
            payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
            token_payload=_token(org_id),
            db=db_session,
        )

    assert "SMTP_HOST is required" in exc.value.message
    refreshed = SubmissionPacketService(db_session).get_packet(str(packet.id), str(load.id), org_id)
    assert refreshed.status == "ready"


def test_successful_send_attaches_zip_logs_events_and_marks_sent(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    org_id = "00000000-0000-0000-0000-000000008021"
    load, packet = _seed_packet(db_session, organization_id=org_id)
    captured: dict[str, object] = {}

    def _mock_send(self, **kwargs: object):
        captured.update(kwargs)
        return {
            "provider": "smtp",
            "accepted": True,
            "provider_message_id": "msg-123",
            "error_message": None,
        }

    monkeypatch.setattr("app.api.v1.loads.PacketEmailService.send_email_with_attachments", _mock_send)

    result = send_submission_packet_email(
        load_id=load.id,
        packet_id=packet.id,
        payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
        token_payload=_token(org_id),
        db=db_session,
    )

    attachments = captured.get("attachments")
    assert isinstance(attachments, list)
    assert attachments
    assert attachments[0]["content_type"] == "application/zip"
    assert attachments[0]["bytes"]
    refreshed = SubmissionPacketService(db_session).get_packet(str(packet.id), str(load.id), org_id)
    event_types = [event.event_type for event in refreshed.events]
    assert "packet_email_send_attempt" in event_types
    assert "packet_email_sent" in event_types
    assert refreshed.status == "sent"
    assert refreshed.sent_at is not None
    assert result.meta["email_send_result"]["accepted"] is True


def test_failed_send_logs_failed_event_and_keeps_packet_not_sent(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    org_id = "00000000-0000-0000-0000-000000008031"
    load, packet = _seed_packet(db_session, organization_id=org_id)

    monkeypatch.setattr(
        "app.api.v1.loads.PacketEmailService.send_email_with_attachments",
        lambda self, **_: {
            "provider": "smtp",
            "accepted": False,
            "provider_message_id": None,
            "error_message": "Email provider send failed.",
        },
    )

    with pytest.raises(ValidationError):
        send_submission_packet_email(
            load_id=load.id,
            packet_id=packet.id,
            payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
            token_payload=_token(org_id),
            db=db_session,
        )

    refreshed = SubmissionPacketService(db_session).get_packet(str(packet.id), str(load.id), org_id)
    assert refreshed.status == "ready"
    assert any(event.event_type == "packet_email_failed" for event in refreshed.events)


def test_driver_cannot_send_packet_email(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000008041"
    load, packet = _seed_packet(db_session, organization_id=org_id)

    with pytest.raises(ForbiddenError):
        send_submission_packet_email(
            load_id=load.id,
            packet_id=packet.id,
            payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
            token_payload=_token(org_id, role="driver"),
            db=db_session,
        )


def test_cross_org_send_denied(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000008051"
    other_org_id = "00000000-0000-0000-0000-000000008052"
    load, packet = _seed_packet(db_session, organization_id=org_id)

    with pytest.raises(UnauthorizedError):
        send_submission_packet_email(
            load_id=load.id,
            packet_id=packet.id,
            payload=SubmissionPacketSendEmailRequest(to_email="ap@broker.test"),
            token_payload=_token(other_org_id),
            db=db_session,
        )
