from __future__ import annotations

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
