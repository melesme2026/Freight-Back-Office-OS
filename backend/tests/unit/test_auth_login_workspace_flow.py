from __future__ import annotations

import uuid

from fastapi.responses import JSONResponse
import pytest

from app.api.v1.auth import LoginRequestBody, get_current_user, login
from app.core.exceptions import AppError
from app.core.security import decode_token, hash_password
from app.domain.enums.role import Role
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser


def _seed_org(db_session, org_id: uuid.UUID, *, name: str, slug: str) -> None:
    db_session.add(
        Organization(
            id=org_id,
            name=name,
            slug=slug,
            is_active=True,
            billing_provider="none",
            billing_status="trial",
            plan_code="starter",
        )
    )


def _seed_user(db_session, *, org_id: uuid.UUID, email: str, role: Role, password: str) -> StaffUser:
    user = StaffUser(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=email,
        full_name=f"{role.value.title()} User",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    return user


def test_single_workspace_staff_login_succeeds(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Adwa Express LLC", slug="adwa-express")
    _seed_user(db_session, org_id=org_id, email="staff@example.com", role=Role.OWNER, password="Owner123!")
    db_session.commit()

    response = login(LoginRequestBody(email="staff@example.com", password="Owner123!"), db=db_session, x_organization_id=None)

    assert response.data.user.organization_id == str(org_id)
    assert response.data.user.role == Role.OWNER.value
    claims = decode_token(response.data.access_token)
    assert claims.get("organization_id") == str(org_id)
    assert claims.get("sub")


def test_single_workspace_driver_login_and_me_include_driver_context(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Adwa Driver Ops", slug="adwa-driver-ops")
    user = _seed_user(db_session, org_id=org_id, email="driver@example.com", role=Role.DRIVER, password="Driver123!")
    driver = Driver(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_account_id=None,
        full_name="Driver Example",
        phone="+15550001111",
        email="driver@example.com",
        is_active=True,
    )
    db_session.add(driver)
    db_session.commit()

    response = login(LoginRequestBody(email="driver@example.com", password="Driver123!"), db=db_session, x_organization_id=None)
    claims = decode_token(response.data.access_token)
    assert claims.get("organization_id") == str(org_id)
    assert claims.get("driver_id") == str(driver.id)
    assert claims.get("sub") == str(user.id)

    me = get_current_user(token=response.data.access_token, db=db_session)
    assert me.data.organization_id == str(org_id)
    assert me.data.role == Role.DRIVER.value
    assert me.data.driver_id == str(driver.id)


def test_multi_workspace_login_requires_explicit_organization_selection(db_session) -> None:
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    _seed_org(db_session, org_a, name="Adwa Express LLC", slug="adwa-express")
    _seed_org(db_session, org_b, name="Adwa Driver Ops", slug="adwa-driver-ops")
    _seed_user(db_session, org_id=org_a, email="multi@example.com", role=Role.OWNER, password="Owner123!")
    _seed_user(db_session, org_id=org_b, email="multi@example.com", role=Role.DRIVER, password="Owner123!")
    db_session.add(
        Driver(
            id=uuid.uuid4(),
            organization_id=org_b,
            customer_account_id=None,
            full_name="Multi Driver",
            phone="+15550002222",
            email="multi@example.com",
            is_active=True,
        )
    )
    db_session.commit()

    initial = login(LoginRequestBody(email="multi@example.com", password="Owner123!"), db=db_session, x_organization_id=None)
    assert isinstance(initial, JSONResponse)
    assert initial.status_code == 422
    payload = initial.body.decode("utf-8")
    assert "multiple_organizations" in payload
    assert "Adwa Express LLC" in payload
    assert "Adwa Driver Ops" in payload

    selected = login(
        LoginRequestBody(email="multi@example.com", password="Owner123!", organization_id=org_b),
        db=db_session,
        x_organization_id=None,
    )
    selected_claims = decode_token(selected.data.access_token)
    assert selected.data.user.organization_id == str(org_b)
    assert selected_claims.get("organization_id") == str(org_b)


def test_multi_workspace_login_rejects_invalid_organization_id(db_session) -> None:
    org_a = uuid.uuid4()
    _seed_org(db_session, org_a, name="Adwa Express LLC", slug="adwa-express")
    _seed_user(db_session, org_id=org_a, email="multi@example.com", role=Role.OWNER, password="Owner123!")
    db_session.commit()

    invalid_org = uuid.uuid4()
    with pytest.raises(AppError) as exc_info:
        login(
            LoginRequestBody(email="multi@example.com", password="Owner123!", organization_id=invalid_org),
            db=db_session,
            x_organization_id=None,
        )

    assert exc_info.value.code == "invalid_organization_selection"
