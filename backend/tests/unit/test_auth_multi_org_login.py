from __future__ import annotations

import uuid

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.domain.enums.role import Role
from app.domain.models.organization import Organization
from app.domain.models.staff_user import StaffUser
from app.services.auth.auth_service import AuthService


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


def test_multi_organization_login_returns_workspace_options(db_session) -> None:
    email = "multi@example.com"
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    _seed_org(db_session, org_a, name="Adwa Express LLC", slug="adwa-express")
    _seed_org(db_session, org_b, name="Adwa Driver Ops", slug="adwa-driver-ops")

    db_session.add_all(
        [
            StaffUser(
                id=uuid.uuid4(),
                organization_id=org_a,
                email=email,
                full_name="Ops Owner",
                password_hash=hash_password("Owner123!"),
                role=Role.OWNER,
                is_active=True,
            ),
            StaffUser(
                id=uuid.uuid4(),
                organization_id=org_b,
                email=email,
                full_name="Driver Staff",
                password_hash=hash_password("Owner123!"),
                role=Role.DRIVER,
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    auth_service = AuthService(db_session)

    try:
        auth_service.resolve_organization_id_for_login(email=email)
    except AppError as exc:
        assert exc.code == "multiple_organizations"
        assert exc.status_code == 422
        organizations = exc.details.get("organizations")
        assert isinstance(organizations, list)
        assert len(organizations) == 2
        assert {item["organization_name"] for item in organizations} == {"Adwa Express LLC", "Adwa Driver Ops"}
        assert {item["role"] for item in organizations} == {"owner", "driver"}
    else:
        raise AssertionError("Expected multiple_organizations error for shared email login")
