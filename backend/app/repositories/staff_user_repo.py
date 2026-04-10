from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

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

    def get_by_id(
        self,
        staff_user_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> StaffUser | None:
        normalized_staff_user_id = self._normalize_uuid(
            staff_user_id,
            field_name="staff_user_id",
        )

        stmt = select(StaffUser).where(StaffUser.id == normalized_staff_user_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_email(
        self,
        *,
        organization_id: uuid.UUID | str,
        email: str,
        include_related: bool = False,
    ) -> StaffUser | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )

        stmt = select(StaffUser).where(
            StaffUser.organization_id == normalized_organization_id,
            StaffUser.email == email,
        )

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        role: Role | str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[StaffUser], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_role = self._normalize_role(role)
        normalized_search = search.strip() if search else None

        stmt = select(StaffUser)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(StaffUser)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(StaffUser.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(StaffUser.organization_id == normalized_organization_id)

        if normalized_role is not None:
            stmt = stmt.where(StaffUser.role == normalized_role)
            count_stmt = count_stmt.where(StaffUser.role == normalized_role)

        if is_active is not None:
            stmt = stmt.where(StaffUser.is_active == is_active)
            count_stmt = count_stmt.where(StaffUser.is_active == is_active)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                StaffUser.email.ilike(pattern),
                StaffUser.full_name.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

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

    def _apply_related(self, stmt: Select[tuple[StaffUser]]) -> Select[tuple[StaffUser]]:
        return stmt.options(
            selectinload(StaffUser.organization),
            selectinload(StaffUser.reviewed_loads),
            selectinload(StaffUser.validation_issues_resolved),
            selectinload(StaffUser.workflow_events),
            selectinload(StaffUser.support_tickets_assigned),
            selectinload(StaffUser.notifications_created),
            selectinload(StaffUser.payments_recorded),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    def _normalize_role(self, value: Role | str | None) -> Role | None:
        if value is None:
            return None

        if isinstance(value, Role):
            return value

        normalized = str(value).strip().lower()

        for role in Role:
            if normalized == role.value.lower():
                return role
            if normalized == role.name.lower():
                return role

        raise ValueError(f"Invalid role: {value}")