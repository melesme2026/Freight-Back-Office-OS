from __future__ import annotations

import uuid

from app.core.security import decode_token, hash_password
from app.domain.enums.role import Role
from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.services.auth.auth_service import AuthService


def test_staff_and_driver_authentication_runtime(db_session) -> None:
    organization_id = uuid.uuid4()

    organization = Organization(
        id=organization_id,
        name="Runtime Org",
        slug="runtime-org",
        is_active=True,
        billing_provider="none",
        billing_status="trial",
        plan_code="starter",
    )

    customer_account = CustomerAccount(
        id=uuid.uuid4(),
        organization_id=organization_id,
        account_name="Runtime Customer",
        account_code="RT-1",
        status=CustomerAccountStatus.ACTIVE,
        primary_contact_name="Contact",
        primary_contact_email="contact@example.com",
        primary_contact_phone="+13135550000",
        billing_email="billing@example.com",
        notes=None,
    )

    driver = Driver(
        id=uuid.uuid4(),
        organization_id=organization_id,
        customer_account_id=customer_account.id,
        full_name="Driver One",
        phone="+13135550001",
        email="john.doe@example.com",
        is_active=True,
    )

    staff_admin = StaffUser(
        id=uuid.uuid4(),
        organization_id=organization_id,
        email="admin@runtime.org",
        full_name="Runtime Admin",
        password_hash=hash_password("Admin123!"),
        role=Role.ADMIN,
        is_active=True,
    )

    staff_driver = StaffUser(
        id=uuid.uuid4(),
        organization_id=organization_id,
        email="john.doe@example.com",
        full_name="Driver User",
        password_hash=hash_password("Driver123!"),
        role=Role.DRIVER,
        is_active=True,
    )

    db_session.add_all([organization, customer_account, driver, staff_admin, staff_driver])
    db_session.commit()

    auth_service = AuthService(db_session)

    authenticated_admin = auth_service.authenticate_staff_user(
        organization_id=organization_id,
        email="admin@runtime.org",
        password="Admin123!",
    )
    assert authenticated_admin.id == staff_admin.id

    authenticated_driver = auth_service.authenticate_staff_user(
        organization_id=organization_id,
        email="john.doe@example.com",
        password="Driver123!",
    )
    token = auth_service.build_access_token(authenticated_driver)
    payload = decode_token(token)

    assert payload["role"] == "driver"
    assert payload["driver_id"] == str(driver.id)
