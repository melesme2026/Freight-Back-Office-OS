from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, UnauthorizedError
from app.domain.models.organization import Organization
from app.core.security import create_access_token, verify_password
from app.domain.models.staff_user import StaffUser
from app.repositories.driver_repo import DriverRepository
from app.repositories.staff_user_repo import StaffUserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.staff_user_repo = StaffUserRepository(db)
        self.driver_repo = DriverRepository(db)

    def authenticate_staff_user(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        password: str,
    ) -> StaffUser:
        normalized_email = email.strip().lower()

        user = self.staff_user_repo.get_by_email(
            organization_id=organization_id,
            email=normalized_email,
        )

        if user is None:
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        user.last_login_at = datetime.now(timezone.utc)
        user = self.staff_user_repo.update(user)

        return user

    def resolve_organization_id_for_login(
        self,
        *,
        email: str,
        organization_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        if organization_id is not None:
            return organization_id

        normalized_email = email.strip().lower()
        stmt = (
            select(StaffUser.organization_id, StaffUser.role, Organization.name)
            .join(Organization, StaffUser.organization_id == Organization.id)
            .where(StaffUser.email == normalized_email)
            .distinct()
        )
        organization_records = list(self.db.execute(stmt).all())

        if not organization_records:
            raise UnauthorizedError("Invalid email or password")

        if len(organization_records) > 1:
            organizations = [
                {
                    "organization_id": str(record.organization_id),
                    "organization_name": record.name,
                    "role": str(getattr(record.role, "value", record.role)).lower(),
                }
                for record in organization_records
            ]
            raise AppError(
                "This email is linked to multiple workspaces. Select the workspace you want to access.",
                code="multiple_organizations",
                status_code=422,
                details={"email": normalized_email, "organization_count": len(organizations), "organizations": organizations},
            )

        return organization_records[0].organization_id

    def authenticate_user_for_login(
        self,
        *,
        email: str,
        password: str,
        organization_id: uuid.UUID | None = None,
    ) -> StaffUser:
        normalized_email = email.strip().lower()
        stmt = (
            select(StaffUser, Organization.name)
            .join(Organization, StaffUser.organization_id == Organization.id)
            .where(StaffUser.email == normalized_email, StaffUser.is_active.is_(True))
        )
        organization_records = list(self.db.execute(stmt).all())

        if not organization_records:
            raise UnauthorizedError("Invalid email or password")

        if organization_id is not None:
            selected = [record for record in organization_records if record.StaffUser.organization_id == organization_id]
            if not selected:
                raise AppError(
                    "Invalid workspace selection.",
                    code="invalid_organization_selection",
                    status_code=422,
                )
            organization_records = selected

        password_matches = [record for record in organization_records if verify_password(password, record.StaffUser.password_hash)]
        if not password_matches:
            raise UnauthorizedError("Invalid email or password")

        active_matches = []
        inactive_driver_matches = []
        for record in password_matches:
            role_value = str(getattr(record.StaffUser.role, "value", record.StaffUser.role)).lower()
            if role_value != "driver":
                active_matches.append(record)
                continue

            driver = self.driver_repo.get_by_email(
                organization_id=record.StaffUser.organization_id,
                email=normalized_email,
                include_related=False,
            )
            if driver is None:
                raise UnauthorizedError("Driver account is not linked to a driver profile")
            if not driver.is_active:
                inactive_driver_matches.append(record)
                continue
            active_matches.append(record)

        if not active_matches:
            if inactive_driver_matches:
                raise UnauthorizedError("This driver account is inactive. Contact your dispatcher.")
            raise UnauthorizedError("Invalid email or password")
        password_matches = active_matches

        if organization_id is None and len(password_matches) > 1:
            organizations_by_id: dict[uuid.UUID, dict[str, object]] = {}
            for record in password_matches:
                org_id = record.StaffUser.organization_id
                role_value = str(getattr(record.StaffUser.role, "value", record.StaffUser.role)).lower()
                existing = organizations_by_id.get(org_id)
                if existing is None:
                    organizations_by_id[org_id] = {
                        "organization_id": str(org_id),
                        "organization_name": record.name,
                        "roles": {role_value},
                    }
                else:
                    roles = existing["roles"]
                    assert isinstance(roles, set)
                    roles.add(role_value)

            organizations = []
            for item in sorted(organizations_by_id.values(), key=lambda value: (str(value.get("organization_name") or "").lower(), str(value["organization_id"]))):
                roles = sorted(item["roles"]) if isinstance(item["roles"], set) else []
                organizations.append(
                    {
                        "organization_id": item["organization_id"],
                        "organization_name": item.get("organization_name"),
                        "role": "/".join(roles),
                    }
                )

            raise AppError(
                "This email is linked to multiple workspaces.",
                code="multiple_organizations",
                status_code=422,
                details={"organizations": organizations},
            )

        user = password_matches[0].StaffUser
        user.last_login_at = datetime.now(timezone.utc)
        return self.staff_user_repo.update(user)

    def build_access_token(self, user: StaffUser) -> str:
        role_value = str(getattr(user.role, "value", user.role)).lower()
        additional_claims: dict[str, str] = {
            "organization_id": str(user.organization_id),
            "email": user.email,
            "role": role_value,
        }

        if role_value == "driver":
            driver = self.driver_repo.get_by_email(
                organization_id=user.organization_id,
                email=user.email,
                include_related=False,
            )
            if driver is None:
                raise UnauthorizedError("Driver account is not linked to a driver profile")
            if not driver.is_active:
                raise UnauthorizedError("This driver account is inactive. Contact your dispatcher.")
            additional_claims["driver_id"] = str(driver.id)

        return create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims,
        )
