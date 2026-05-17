from __future__ import annotations

import time
import uuid

import pytest
from app.api.v1.auth import LoginRequestBody, driver_login
from app.api.v1.carrier_profile import get_carrier_profile
from app.api.v1.drivers import list_drivers
from app.api.v1.staff_users import list_staff_users
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.domain.enums.role import Role
from app.domain.models.carrier_profile import CarrierProfile
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.main import create_app


def _seed_org(db_session, org_id: uuid.UUID) -> None:
    db_session.add(
        Organization(
            id=org_id,
            name="P0 Route Org",
            slug=f"p0-route-{org_id.hex[:8]}",
            is_active=True,
            billing_provider="none",
            billing_status="trial",
            plan_code="starter",
        )
    )


def _seed_staff(
    db_session,
    *,
    org_id: uuid.UUID,
    email: str,
    password: str,
    role: Role = Role.OWNER,
    is_active: bool = True,
) -> StaffUser:
    user = StaffUser(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=email,
        full_name="P0 Staff",
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    return user


def _seed_driver_profile(
    db_session, *, org_id: uuid.UUID, email: str, is_active: bool = True
) -> Driver:
    driver = Driver(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_account_id=None,
        full_name="P0 Driver",
        phone="5550100",
        email=email,
        is_active=is_active,
    )
    db_session.add(driver)
    return driver


def _seed_carrier_profile(db_session, *, org_id: uuid.UUID) -> None:
    db_session.add(
        CarrierProfile(
            id=uuid.uuid4(),
            organization_id=org_id,
            legal_name="P0 Freight LLC",
            address_line1="1 Fast Way",
            address_line2=None,
            city="Atlanta",
            state="GA",
            zip="30301",
            country="USA",
            phone="5550101",
            email="ops@example.com",
            mc_number="MC123",
            dot_number="DOT123",
            remit_to_name="P0 Freight LLC",
            remit_to_address="1 Fast Way, Atlanta, GA 30301",
            remit_to_notes=None,
        )
    )


def test_p0_routes_are_registered() -> None:
    app = create_app()
    registered = [(route.path, set(route.methods or [])) for route in app.routes]

    expected = [
        ("/api/v1/auth/login", ["POST"]),
        ("/api/v1/auth/driver-login", ["POST"]),
        ("/api/v1/staff-users", ["GET"]),
        ("/api/v1/drivers", ["GET"]),
        ("/api/v1/customer-accounts", ["GET"]),
        ("/api/v1/dashboard", ["GET"]),
        ("/api/v1/carrier-profile", ["GET"]),
        ("/api/v1/settings/carrier-profile", ["GET"]),
        ("/api/v1/loads", ["GET"]),
        ("/api/v1/documents", ["GET"]),
        ("/api/v1/review-queue", ["GET"]),
    ]

    for path, methods in expected:
        assert any(
            path == route_path and set(methods).issubset(route_methods)
            for route_path, route_methods in registered
        ), path


def test_driver_login_valid_invalid_and_inactive_paths_are_fast(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id)
    valid_user = _seed_staff(
        db_session,
        org_id=org_id,
        email="driver-valid@example.com",
        password="Driver123!",
        role=Role.DRIVER,
    )
    valid_driver = _seed_driver_profile(
        db_session, org_id=org_id, email="driver-valid@example.com", is_active=True
    )
    _seed_staff(
        db_session,
        org_id=org_id,
        email="driver-inactive@example.com",
        password="Driver123!",
        role=Role.DRIVER,
    )
    _seed_driver_profile(
        db_session, org_id=org_id, email="driver-inactive@example.com", is_active=False
    )
    db_session.commit()

    started = time.perf_counter()
    response = driver_login(
        LoginRequestBody(email="DRIVER-VALID@example.com", password="Driver123!"),
        db=db_session,
        x_organization_id=str(org_id),
    )
    assert (time.perf_counter() - started) < 2
    assert response.data.user.role == Role.DRIVER.value
    assert response.data.user.driver_id == str(valid_driver.id)
    assert response.data.user.id == str(valid_user.id)

    started = time.perf_counter()
    with pytest.raises(AppError) as invalid_exc:
        driver_login(
            LoginRequestBody(email="driver-valid@example.com", password="wrong"),
            db=db_session,
            x_organization_id=str(org_id),
        )
    assert (time.perf_counter() - started) < 2
    assert invalid_exc.value.status_code == 401

    started = time.perf_counter()
    with pytest.raises(AppError) as inactive_exc:
        driver_login(
            LoginRequestBody(email="driver-inactive@example.com", password="Driver123!"),
            db=db_session,
            x_organization_id=str(org_id),
        )
    assert (time.perf_counter() - started) < 2
    assert inactive_exc.value.status_code == 403


def test_staff_users_drivers_and_settings_response_shapes_are_fast(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id)
    _seed_staff(db_session, org_id=org_id, email="owner@example.com", password="Owner123!")
    _seed_staff(
        db_session,
        org_id=org_id,
        email="ops@example.com",
        password="Ops12345!",
        role=Role.OPS_AGENT,
    )
    _seed_driver_profile(db_session, org_id=org_id, email="driver@example.com")
    _seed_carrier_profile(db_session, org_id=org_id)
    db_session.commit()

    token_payload = {"organization_id": str(org_id), "role": "owner"}

    started = time.perf_counter()
    staff_response = list_staff_users(
        page=1, page_size=25, token_payload=token_payload, db=db_session
    )
    assert (time.perf_counter() - started) < 2
    assert isinstance(staff_response.data, list)
    assert staff_response.meta["page_size"] == 25
    assert all("password_hash" not in item for item in staff_response.data)

    started = time.perf_counter()
    drivers_response = list_drivers(
        page=1, page_size=25, token_payload=token_payload, db=db_session
    )
    assert (time.perf_counter() - started) < 2
    assert isinstance(drivers_response.data, list)
    assert {"id", "full_name", "is_active"}.issubset(drivers_response.data[0])

    started = time.perf_counter()
    settings_response = get_carrier_profile(token_payload=token_payload, db=db_session)
    assert (time.perf_counter() - started) < 2
    assert settings_response.data["organization_id"] == str(org_id)
    assert settings_response.data["legal_name"] == "P0 Freight LLC"
