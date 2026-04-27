from __future__ import annotations

import uuid

import pytest

from app.api.v1.auth import LoginRequestBody, login
from app.api.v1.drivers import (
    DriverCreateRequest,
    DriverUpdateRequest,
    create_driver,
    reactivate_driver,
    update_driver,
)
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.domain.enums.channel import Channel
from app.domain.enums.role import Role
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.services.loads.load_service import LoadService


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


def _seed_customer(db_session, *, org_id: uuid.UUID) -> uuid.UUID:
    customer_id = uuid.uuid4()
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name="Lifecycle Customer",
            account_code="LC-001",
            status="active",
        )
    )
    return customer_id


def _seed_driver_staff_user(db_session, *, org_id: uuid.UUID, email: str, password: str = "Driver123!") -> None:
    db_session.add(
        StaffUser(
            id=uuid.uuid4(),
            organization_id=org_id,
            email=email,
            full_name="Driver User",
            password_hash=hash_password(password),
            role=Role.DRIVER,
            is_active=True,
        )
    )


def test_create_driver_blocks_duplicate_active_email(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Duplicate Active Org", slug="duplicate-active-org")
    customer_id = _seed_customer(db_session, org_id=org_id)
    db_session.add(
        Driver(
            id=uuid.uuid4(),
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name="Existing Active Driver",
            phone="5551000",
            email="driver@example.com",
            is_active=True,
        )
    )
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        create_driver(
            DriverCreateRequest(
                organization_id=org_id,
                customer_account_id=customer_id,
                full_name="Duplicate Driver",
                phone="5551001",
                email="Driver@Example.com",
                is_active=True,
            ),
            token_payload={"organization_id": str(org_id), "role": "owner"},
            db=db_session,
        )

    assert exc_info.value.status_code == 422
    assert str(exc_info.value) == "A driver with this email already exists in this workspace."


def test_create_driver_with_inactive_duplicate_requires_reactivation(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Inactive Duplicate Org", slug="inactive-duplicate-org")
    customer_id = _seed_customer(db_session, org_id=org_id)
    existing = Driver(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_account_id=customer_id,
        full_name="Existing Inactive Driver",
        phone="5552000",
        email="inactive@example.com",
        is_active=False,
    )
    db_session.add(existing)
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        create_driver(
            DriverCreateRequest(
                organization_id=org_id,
                customer_account_id=customer_id,
                full_name="Replacement Driver",
                phone="5552001",
                email="inactive@example.com",
                is_active=True,
            ),
            token_payload={"organization_id": str(org_id), "role": "owner"},
            db=db_session,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "driver_reactivation_required"
    assert exc_info.value.details["driver_id"] == str(existing.id)


def test_reactivate_driver_restores_login_and_preserves_driver_id(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Reactivate Org", slug="reactivate-org")
    customer_id = _seed_customer(db_session, org_id=org_id)
    _seed_driver_staff_user(db_session, org_id=org_id, email="reactivate@example.com")

    driver = Driver(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_account_id=customer_id,
        full_name="Reactivate Me",
        phone="5553000",
        email="reactivate@example.com",
        is_active=False,
    )
    db_session.add(driver)
    db_session.commit()

    with pytest.raises(AppError):
        login(LoginRequestBody(email="reactivate@example.com", password="Driver123!"), db=db_session, x_organization_id=None)

    reactivated_response = reactivate_driver(
        driver.id,
        token_payload={"organization_id": str(org_id), "role": "owner"},
        db=db_session,
    )
    assert reactivated_response.data["id"] == str(driver.id)
    assert reactivated_response.data["is_active"] is True

    post_reactivate_login = login(LoginRequestBody(email="reactivate@example.com", password="Driver123!"), db=db_session, x_organization_id=None)
    assert post_reactivate_login.data.user.organization_id == str(org_id)


def test_deactivation_preserves_existing_load_history(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="History Org", slug="history-org")
    customer_id = _seed_customer(db_session, org_id=org_id)

    driver = Driver(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_account_id=customer_id,
        full_name="History Driver",
        phone="5554000",
        email="history@example.com",
        is_active=True,
    )
    db_session.add(driver)
    db_session.flush()

    load = LoadService(db_session).create_load(
        organization_id=str(org_id),
        customer_account_id=str(customer_id),
        driver_id=str(driver.id),
        source_channel=Channel.MANUAL,
        load_number="HIST-1",
    )
    db_session.commit()

    update_driver(
        driver.id,
        DriverUpdateRequest(is_active=False),
        token_payload={"organization_id": str(org_id), "role": "owner"},
        db=db_session,
    )

    persisted_load = LoadService(db_session).get_load(str(load.id))
    assert str(persisted_load.driver_id) == str(driver.id)
