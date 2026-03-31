from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.role import Role
from app.domain.models.staff_user import StaffUser


class StaffUserRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, staff_user: StaffUser) -> StaffUser:
        self.db.add(staff_user)
        self.db.flush()
        self.db.refresh(staff_user)
        return staff_user

    def get_by_id(self, staff_user_id: uuid.UUID) -> StaffUser | None:
        stmt = select(StaffUser).where(StaffUser.id == staff_user_id)
        return self.db.scalar(stmt)

    def get_by_email(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
    ) -> StaffUser | None:
        stmt = select(StaffUser).where(
            StaffUser.organization_id == organization_id,
            StaffUser.email == email,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[StaffUser], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(StaffUser)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(StaffUser)

        if organization_id is not None:
            stmt = stmt.where(StaffUser.organization_id == organization_id)
            count_stmt = count_stmt.where(StaffUser.organization_id == organization_id)

        if role is not None:
            stmt = stmt.where(StaffUser.role == role)
            count_stmt = count_stmt.where(StaffUser.role == role)

        if is_active is not None:
            stmt = stmt.where(StaffUser.is_active == is_active)
            count_stmt = count_stmt.where(StaffUser.is_active == is_active)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                StaffUser.email.ilike(pattern),
                StaffUser.full_name.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(StaffUser.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, staff_user: StaffUser) -> StaffUser:
        self.db.add(staff_user)
        self.db.flush()
        self.db.refresh(staff_user)
        return staff_user

    def delete(self, staff_user: StaffUser) -> None:
        self.db.delete(staff_user)
        self.db.flush()