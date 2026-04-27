from __future__ import annotations

import uuid

import pytest

from app.api.v1.auth import InviteUserRequest, invite_user, login, LoginRequestBody
from app.api.v1.staff_users import (
    StaffUserRemoveRequest,
    StaffUserUpdateRequest,
    list_staff_users,
    remove_staff_user,
    update_staff_user,
)
from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password
from app.domain.enums.role import Role
from app.domain.models.audit_log import AuditLog
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


def _seed_user(
    db_session,
    *,
    org_id: uuid.UUID,
    role: Role,
    email: str,
    is_active: bool = True,
) -> StaffUser:
    user = StaffUser(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=email,
        full_name=email.split("@")[0],
        password_hash=hash_password("Pass123!"),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_owner_can_invite_staff_and_audit_is_created(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Invite Org", slug="invite-org")
    owner = _seed_user(db_session, org_id=org_id, role=Role.OWNER, email="owner@invite.org")
    db_session.commit()

    token = create_access_token(subject=str(owner.id), additional_claims={"organization_id": str(org_id), "role": "owner"})
    response = invite_user(
        InviteUserRequest(
            organization_id=org_id,
            full_name="Ops Agent",
            email="ops@invite.org",
            role="ops_agent",
        ),
        token=token,
        db=db_session,
    )

    assert response.data["invite_sent"] is True
    log = db_session.query(AuditLog).filter(AuditLog.action == "staff_invited").one()
    assert str(log.organization_id) == str(org_id)


def test_ops_agent_cannot_remove_staff(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Ops Org", slug="ops-org")
    ops = _seed_user(db_session, org_id=org_id, role=Role.OPS_AGENT, email="ops@ops.org")
    target = _seed_user(db_session, org_id=org_id, role=Role.BILLING_ADMIN, email="billing@ops.org")
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        remove_staff_user(
            target.id,
            StaffUserRemoveRequest(reason="test"),
            token_payload={"organization_id": str(org_id), "sub": str(ops.id), "role": "ops_agent"},
            db=db_session,
        )

    assert exc_info.value.code == "forbidden_action"


def test_admin_cannot_disable_owner(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Admin Org", slug="admin-org")
    owner = _seed_user(db_session, org_id=org_id, role=Role.OWNER, email="owner@admin.org")
    admin = _seed_user(db_session, org_id=org_id, role=Role.ADMIN, email="admin@admin.org")
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        update_staff_user(
            owner.id,
            StaffUserUpdateRequest(is_active=False),
            token_payload={"organization_id": str(org_id), "sub": str(admin.id), "role": "admin"},
            db=db_session,
        )

    assert exc_info.value.code == "cannot_modify_owner"


def test_cannot_remove_final_active_admin_or_owner(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Final Org", slug="final-org")
    owner = _seed_user(db_session, org_id=org_id, role=Role.OWNER, email="owner@final.org")
    staff = _seed_user(db_session, org_id=org_id, role=Role.OPS_AGENT, email="ops@final.org")
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        remove_staff_user(
            owner.id,
            StaffUserRemoveRequest(),
            token_payload={"organization_id": str(org_id), "sub": str(owner.id), "role": "owner"},
            db=db_session,
        )

    assert exc_info.value.code in {"cannot_modify_owner", "final_admin_required", "cannot_remove_self_as_final_admin"}

    updated_staff = update_staff_user(
        staff.id,
        StaffUserUpdateRequest(is_active=False),
        token_payload={"organization_id": str(org_id), "sub": str(owner.id), "role": "owner"},
        db=db_session,
    )
    assert updated_staff.data["is_active"] is False


def test_cross_org_modification_is_blocked(db_session) -> None:
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    _seed_org(db_session, org_a, name="A Org", slug="a-org")
    _seed_org(db_session, org_b, name="B Org", slug="b-org")
    owner_a = _seed_user(db_session, org_id=org_a, role=Role.OWNER, email="owner@a.org")
    target_b = _seed_user(db_session, org_id=org_b, role=Role.OPS_AGENT, email="ops@b.org")
    db_session.commit()

    with pytest.raises(AppError):
        remove_staff_user(
            target_b.id,
            StaffUserRemoveRequest(),
            token_payload={"organization_id": str(org_a), "sub": str(owner_a.id), "role": "owner"},
            db=db_session,
        )


def test_removed_and_disabled_users_cannot_login(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="Login Org", slug="login-org")
    owner = _seed_user(db_session, org_id=org_id, role=Role.OWNER, email="owner@login.org")
    disabled = _seed_user(db_session, org_id=org_id, role=Role.OPS_AGENT, email="disabled@login.org", is_active=False)
    removed = _seed_user(db_session, org_id=org_id, role=Role.BILLING_ADMIN, email="removed@login.org", is_active=True)
    db_session.commit()

    remove_staff_user(
        removed.id,
        StaffUserRemoveRequest(),
        token_payload={"organization_id": str(org_id), "sub": str(owner.id), "role": "owner"},
        db=db_session,
    )

    with pytest.raises(AppError):
        login(LoginRequestBody(email=disabled.email, password="Pass123!", organization_id=org_id), db=db_session, x_organization_id=None)
    with pytest.raises(AppError):
        login(LoginRequestBody(email=removed.email, password="Pass123!", organization_id=org_id), db=db_session, x_organization_id=None)


def test_removed_members_hidden_from_default_team_list_and_audited(db_session) -> None:
    org_id = uuid.uuid4()
    _seed_org(db_session, org_id, name="List Org", slug="list-org")
    owner = _seed_user(db_session, org_id=org_id, role=Role.OWNER, email="owner@list.org")
    target = _seed_user(db_session, org_id=org_id, role=Role.OPS_AGENT, email="ops@list.org")
    db_session.commit()

    remove_staff_user(
        target.id,
        StaffUserRemoveRequest(reason="cleanup"),
        token_payload={"organization_id": str(org_id), "sub": str(owner.id), "role": "owner"},
        db=db_session,
    )

    default_list = list_staff_users(
        token_payload={"organization_id": str(org_id), "role": "owner"},
        db=db_session,
        page=1,
        page_size=100,
    )
    assert all(item["id"] != str(target.id) for item in default_list.data)

    include_removed = list_staff_users(
        token_payload={"organization_id": str(org_id), "role": "owner"},
        db=db_session,
        page=1,
        page_size=100,
        include_removed=True,
    )
    removed_items = [item for item in include_removed.data if item["id"] == str(target.id)]
    assert removed_items and removed_items[0]["status"] == "removed"

    actions = {entry.action for entry in db_session.query(AuditLog).all()}
    assert "staff_removed" in actions
