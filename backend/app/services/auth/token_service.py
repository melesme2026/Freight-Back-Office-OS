from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.domain.models.staff_user import StaffUser
from app.repositories.staff_user_repo import StaffUserRepository


class TokenService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.staff_user_repo = StaffUserRepository(db)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        return decode_token(token)

    def get_current_staff_user(self, token: str) -> StaffUser:
        payload = self.decode_access_token(token)

        subject = payload.get("sub")
        if not subject:
            raise UnauthorizedError("Token subject is missing")

        try:
            user_id = uuid.UUID(str(subject))
        except (TypeError, ValueError) as exc:
            raise UnauthorizedError("Invalid token subject") from exc

        token_organization_id = payload.get("organization_id")
        if not token_organization_id:
            raise UnauthorizedError("Token organization_id is missing")

        try:
            organization_id = uuid.UUID(str(token_organization_id))
        except (TypeError, ValueError) as exc:
            raise UnauthorizedError("Invalid token organization_id") from exc

        user = self.staff_user_repo.get_by_id(user_id, include_related=True)
        if user is None:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise UnauthorizedError("User account is inactive")

        if user.organization_id != organization_id:
            raise UnauthorizedError("Token organization does not match user organization")

        return user