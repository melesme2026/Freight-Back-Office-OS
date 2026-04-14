from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError, ValidationError
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
        stmt = select(StaffUser.organization_id).where(StaffUser.email == normalized_email).distinct()
        organization_ids = list(self.db.scalars(stmt).all())

        if not organization_ids:
            raise UnauthorizedError("Invalid email or password")

        if len(organization_ids) > 1:
            raise ValidationError(
                "Multiple organizations are associated with this email. Use advanced login with organization_id.",
                details={"email": normalized_email, "organization_count": len(organization_ids)},
            )

        return organization_ids[0]

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
            additional_claims["driver_id"] = str(driver.id)

        return create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims,
        )
