from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.domain.models.driver import Driver
from app.domain.models.staff_user import StaffUser
from app.domain.enums.role import Role
from app.core.exceptions import UnauthorizedError
from app.core.security import create_action_token
from app.api.v1.auth import (
    ActivateAccountRequest,
    ConfirmPasswordResetRequest,
    InviteUserRequest,
    PasswordResetRequest,
    SignupRequestBody,
    activate_account,
    invite_user,
    request_password_reset,
    reset_password,
    signup,
)
from app.api.v1.staff_users import StaffUserCreateRequest, create_staff_user


def test_signup_creates_owner_session(db_session) -> None:
    response = signup(
        SignupRequestBody(
            full_name="Public Owner",
            organization_name="Public Launch Freight",
            email="owner@publiclaunchfreight.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    assert response.data.access_token
    assert response.data.user.role == "owner"
    assert response.data.user.organization_id


def test_public_signup_is_owner_only(db_session) -> None:
    response = signup(
        SignupRequestBody(
            full_name="Bootstrap Owner",
            organization_name="Bootstrap Freight",
            email="bootstrap.owner@freight.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    assert response.data.user.role == Role.OWNER.value


def test_invite_activate_and_reset_password_flow(db_session) -> None:
    signup_response = signup(
        SignupRequestBody(
            full_name="Ops Owner",
            organization_name="Ops Public Freight",
            email="ops.owner@opsfreight.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    owner_token = signup_response.data.access_token
    organization_id = signup_response.data.user.organization_id

    driver_profile = Driver(
        organization_id=organization_id,
        customer_account_id=None,
        full_name="Driver One",
        phone="+15551112222",
        email="driver1@opsfreight.com",
        is_active=True,
    )
    db_session.add(driver_profile)
    db_session.commit()

    invite_response = invite_user(
        InviteUserRequest(
            email="driver1@opsfreight.com",
            full_name="Driver One",
            role="driver",
            organization_id=organization_id,
        ),
        token=owner_token,
        db=db_session,
    )

    activation_token = invite_response.data["activation_token"]
    activated_response = activate_account(
        ActivateAccountRequest(
            token=activation_token,
            password="DriverPass123!",
        ),
        db=db_session,
    )

    assert activated_response.data["activated"] is True

    reset_request_response = request_password_reset(
        PasswordResetRequest(
            email="driver1@opsfreight.com",
        ),
        db=db_session,
    )
    reset_token = reset_request_response.data["reset_token"]

    reset_response = reset_password(
        ConfirmPasswordResetRequest(
            token=reset_token,
            new_password="DriverPass456!",
        ),
        db=db_session,
    )

    assert reset_response.data["password_reset"] is True


def test_admin_cannot_invite_owner_role(db_session) -> None:
    owner_signup = signup(
        SignupRequestBody(
            full_name="Owner User",
            organization_name="Secure Ops Freight",
            email="owner@secureops.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    owner_token = owner_signup.data.access_token
    organization_id = owner_signup.data.user.organization_id

    admin_invite = invite_user(
        InviteUserRequest(
            email="admin@secureops.com",
            full_name="Admin User",
            role=Role.ADMIN.value,
            organization_id=organization_id,
        ),
        token=owner_token,
        db=db_session,
    )
    admin_token = activate_account(
        ActivateAccountRequest(token=admin_invite.data["activation_token"], password="AdminPass123!"),
        db=db_session,
    )
    assert admin_token.data["activated"] is True

    from app.services.auth.auth_service import AuthService

    auth_service = AuthService(db_session)
    admin_user = auth_service.authenticate_staff_user(
        organization_id=organization_id,
        email="admin@secureops.com",
        password="AdminPass123!",
    )
    admin_access_token = auth_service.build_access_token(admin_user)

    try:
        invite_user(
            InviteUserRequest(
                email="coowner@secureops.com",
                full_name="Co Owner",
                role=Role.OWNER.value,
                organization_id=organization_id,
            ),
            token=admin_access_token,
            db=db_session,
        )
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("Expected UnauthorizedError when admin invites owner")


def test_direct_staff_create_rejects_privileged_or_driver_roles(db_session) -> None:
    owner_signup = signup(
        SignupRequestBody(
            full_name="Owner User",
            organization_name="Dispatch Freight",
            email="owner@dispatchfreight.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    token_payload = {
        "organization_id": owner_signup.data.user.organization_id,
        "role": Role.OWNER.value,
    }

    for disallowed_role in (Role.ADMIN.value, Role.OPS_MANAGER.value, Role.DRIVER.value):
        try:
            create_staff_user(
                StaffUserCreateRequest(
                    organization_id=owner_signup.data.user.organization_id,
                    email=f"{disallowed_role}@dispatchfreight.com",
                    full_name="Disallowed User",
                    password="StrongPass123!",
                    role=disallowed_role,
                ),
                token_payload=token_payload,
                db=db_session,
            )
        except UnauthorizedError:
            continue
        else:
            raise AssertionError(f"Expected UnauthorizedError for direct role creation: {disallowed_role}")


    try:
        create_staff_user(
            StaffUserCreateRequest(
                organization_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                email="cross-tenant@dispatchfreight.com",
                full_name="Cross Tenant",
                password="StrongPass123!",
                role=Role.OPS_AGENT.value,
            ),
            token_payload=token_payload,
            db=db_session,
        )
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("Expected UnauthorizedError for cross-tenant staff creation")


def test_activation_rejects_mismatched_organization_token(db_session) -> None:
    owner_signup = signup(
        SignupRequestBody(
            full_name="Owner User",
            organization_name="Token Guard Freight",
            email="owner@tokenguard.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    organization_id = owner_signup.data.user.organization_id
    invite_response = invite_user(
        InviteUserRequest(
            email="ops@tokenguard.com",
            full_name="Ops User",
            role=Role.OPS_AGENT.value,
            organization_id=organization_id,
        ),
        token=owner_signup.data.access_token,
        db=db_session,
    )

    user = db_session.query(StaffUser).filter(StaffUser.email == "ops@tokenguard.com").one()
    forged_token = create_action_token(
        str(user.id),
        token_type="activation",
        additional_claims={"organization_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
    )

    try:
        activate_account(
            ActivateAccountRequest(
                token=forged_token,
                password="OpsPass123!",
            ),
            db=db_session,
        )
    except UnauthorizedError:
        pass
    else:
        raise AssertionError("Expected UnauthorizedError for mismatched activation token organization")


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_public_signup_can_be_disabled(db_session, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "false")
    get_settings.cache_clear()

    with pytest.raises(UnauthorizedError):
        signup(
            SignupRequestBody(
                full_name="Blocked Owner",
                organization_name="Blocked Freight",
                email="blocked@freight.com",
                password="StrongPass123!",
                confirm_password="StrongPass123!",
            ),
            db=db_session,
        )


def test_invite_returns_manual_link_when_email_disabled_outside_dev(db_session, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    monkeypatch.setenv("EMAIL_ENABLED", "false")
    monkeypatch.setenv("EMAIL_DEV_ALLOW_TOKEN_RESPONSE", "false")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-long-enough-12345")
    get_settings.cache_clear()

    signup_response = signup(
        SignupRequestBody(
            full_name="Ops Owner",
            organization_name="Manual Invite Freight",
            email="owner@manualinvite.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        ),
        db=db_session,
    )

    organization_id = signup_response.data.user.organization_id
    driver_profile = Driver(
        organization_id=organization_id,
        customer_account_id=None,
        full_name="Manual Driver",
        phone="+15551113333",
        email="driver@manualinvite.com",
        is_active=True,
    )
    db_session.add(driver_profile)
    db_session.commit()

    invite_response = invite_user(
        InviteUserRequest(
            email="driver@manualinvite.com",
            full_name="Manual Driver",
            role=Role.DRIVER.value,
            organization_id=organization_id,
        ),
        token=signup_response.data.access_token,
        db=db_session,
    )

    assert invite_response.data["email_status"] == "disabled"
    assert "activation_url" in invite_response.data
    assert invite_response.data["activation_url"]
