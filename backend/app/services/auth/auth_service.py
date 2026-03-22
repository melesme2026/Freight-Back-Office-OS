from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.staff_user_repo = StaffUserRepository(db)

    def authenticate_staff_user(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        password: str,
    ) -> StaffUser:
        user = self.staff_user_repo.get_by_email(
            organization_id=organization_id,
            email=email.strip().lower(),
        )

        if user is None:
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        return user

    def build_access_token(self, user: StaffUser) -> str:
        return create_access_token(
            subject=str(user.id),
            additional_claims={
                "organization_id": str(user.organization_id),
                "email": user.email,
                "role": str(user.role),
            },
        )