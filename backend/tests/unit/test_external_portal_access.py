from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile

from app.api.v1.portal import (
    PortalAccessLinkRequest,
    create_portal_access_link,
    get_portal_load,
    upload_portal_document,
)
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.domain.models.audit_log import AuditLog
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.services.loads.load_service import LoadService


def _seed_org_graph(db_session, *, org_id: str, customer_id: str, driver_id: str) -> None:
    db_session.add(Organization(id=org_id, name=f"Org {org_id[-4:]}", slug=f"org-{org_id[-4:]}"))
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name=f"Customer {customer_id[-4:]}",
            account_code=f"C{customer_id[-4:]}",
        )
    )
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name=f"Driver {driver_id[-4:]}",
            phone=f"555{driver_id[-4:]}",
            is_active=True,
        )
    )
    db_session.flush()


def _seed_load(db_session, *, org_id: str, customer_id: str, driver_id: str, load_number: str):
    return LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number=load_number,
        pickup_location="Chicago, IL",
        delivery_location="Atlanta, GA",
    )


def _portal_payload_for(load, *, email: str = "broker@example.com", allow_upload: bool = True) -> dict[str, object]:
    return {
        "organization_id": str(load.organization_id),
        "customer_account_id": str(load.customer_account_id),
        "load_id": str(load.id),
        "role": "external_broker",
        "contact_email": email,
        "allow_packet_download": True,
        "allow_document_upload": allow_upload,
    }


def test_staff_can_create_scoped_expiring_portal_access_link(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000045001"
    customer_id = "00000000-0000-0000-0000-000000045002"
    driver_id = "00000000-0000-0000-0000-000000045003"
    _seed_org_graph(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id)
    load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="PR45")

    response = create_portal_access_link(
        PortalAccessLinkRequest(load_id=load.id, contact_email="Broker@Example.com", role="broker", expires_in_hours=12),
        token_payload={"organization_id": org_id, "role": "admin", "sub": "00000000-0000-0000-0000-000000045099"},
        db=db_session,
    )

    token = response.data["access_token"]
    payload = decode_token(token, expected_token_type="external_portal")
    assert payload["organization_id"] == org_id
    assert payload["customer_account_id"] == customer_id
    assert payload["load_id"] == str(load.id)
    assert payload["role"] == "external_broker"
    assert payload["contact_email"] == "broker@example.com"
    assert response.data["expires_in_hours"] == 12


def test_portal_load_access_is_single_load_scoped(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000045101"
    customer_id = "00000000-0000-0000-0000-000000045102"
    driver_id = "00000000-0000-0000-0000-000000045103"
    _seed_org_graph(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id)
    allowed_load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="ALLOWED")
    other_load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="DENIED")

    response = get_portal_load(load_id=allowed_load.id, token_payload=_portal_payload_for(allowed_load), db=db_session)
    assert response.data["load"]["load_number"] == "ALLOWED"

    with pytest.raises(UnauthorizedError):
        get_portal_load(load_id=other_load.id, token_payload=_portal_payload_for(allowed_load), db=db_session)


def test_portal_org_tampering_is_denied(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000045201"
    other_org_id = "00000000-0000-0000-0000-000000045291"
    customer_id = "00000000-0000-0000-0000-000000045202"
    driver_id = "00000000-0000-0000-0000-000000045203"
    _seed_org_graph(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id)
    load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="TAMPER")
    tampered = _portal_payload_for(load)
    tampered["organization_id"] = other_org_id

    with pytest.raises(UnauthorizedError):
        get_portal_load(load_id=load.id, token_payload=tampered, db=db_session)


def test_external_portal_role_cannot_create_access_links(db_session) -> None:
    with pytest.raises(ForbiddenError):
        create_portal_access_link(
            PortalAccessLinkRequest(load_id="00000000-0000-0000-0000-000000045301", contact_email="x@example.com"),
            token_payload={"organization_id": "00000000-0000-0000-0000-000000045300", "role": "external_broker", "sub": "portal"},
            db=db_session,
        )


def test_portal_upload_is_attributed_and_audit_logged(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000045401"
    customer_id = "00000000-0000-0000-0000-000000045402"
    driver_id = "00000000-0000-0000-0000-000000045403"
    _seed_org_graph(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id)
    load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="UPLOAD")

    response = asyncio.run(
        upload_portal_document(
            load_id=load.id,
            file=UploadFile(
                filename="lumper.pdf",
                file=BytesIO(b"portal-upload-content-pr45"),
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="lumper_receipt",
            token_payload=_portal_payload_for(load, email="ap@example.com"),
            db=db_session,
        )
    )

    assert response.meta["uploaded"] is True
    assert response.meta["attribution"]["contact_email"] == "ap@example.com"
    assert response.data["document_type"] == "lumper_receipt"

    audit_logs = db_session.query(AuditLog).filter(AuditLog.action == "portal.document.uploaded").all()
    assert len(audit_logs) == 1
    assert audit_logs[0].actor_type == "external_portal"
    assert audit_logs[0].metadata_json["contact_email"] == "ap@example.com"


def test_expired_portal_token_is_rejected() -> None:
    from datetime import timedelta

    from app.core.security import create_action_token

    token = create_action_token(
        subject="portal:expired",
        token_type="external_portal",
        additional_claims={
            "organization_id": "00000000-0000-0000-0000-000000045601",
            "customer_account_id": "00000000-0000-0000-0000-000000045602",
            "load_id": "00000000-0000-0000-0000-000000045603",
            "role": "external_broker",
            "contact_email": "expired@example.com",
        },
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(UnauthorizedError):
        decode_token(token, expected_token_type="external_portal")


def test_portal_upload_can_be_disabled_by_scope(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000045501"
    customer_id = "00000000-0000-0000-0000-000000045502"
    driver_id = "00000000-0000-0000-0000-000000045503"
    _seed_org_graph(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id)
    load = _seed_load(db_session, org_id=org_id, customer_id=customer_id, driver_id=driver_id, load_number="NOUPLOAD")

    with pytest.raises(ForbiddenError):
        asyncio.run(
            upload_portal_document(
                load_id=load.id,
                file=UploadFile(filename="doc.pdf", file=BytesIO(b"disabled-upload"), headers=Headers({"content-type": "application/pdf"})),
                document_type="other",
                token_payload=_portal_payload_for(load, allow_upload=False),
                db=db_session,
            )
        )
