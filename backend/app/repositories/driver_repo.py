from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.models.driver import Driver


class DriverRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        self.db.refresh(driver)
        return driver

    def get_by_id(
        self,
        driver_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> Driver | None:
        normalized_driver_id = self._normalize_uuid(driver_id, field_name="driver_id")

        stmt = select(Driver).where(Driver.id == normalized_driver_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_email(
        self,
        *,
        organization_id: uuid.UUID | str,
        email: str,
        include_related: bool = False,
    ) -> Driver | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )
        normalized_email = email.strip().lower()

        stmt = select(Driver).where(
            Driver.organization_id == normalized_organization_id,
            Driver.email == normalized_email,
        )

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[Driver], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_customer_account_id = (
            self._normalize_uuid(customer_account_id, field_name="customer_account_id")
            if customer_account_id is not None
            else None
        )
        normalized_search = search.strip() if search else None

        stmt = select(Driver)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Driver)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(Driver.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(Driver.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Driver.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(Driver.customer_account_id == normalized_customer_account_id)

        if is_active is not None:
            stmt = stmt.where(Driver.is_active == is_active)
            count_stmt = count_stmt.where(Driver.is_active == is_active)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                Driver.full_name.ilike(pattern),
                Driver.phone.ilike(pattern),
                Driver.email.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Driver.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        self.db.refresh(driver)
        return driver

    def delete(self, driver: Driver) -> None:
        self.db.delete(driver)
        self.db.flush()

    def _apply_related(self, stmt: Select[tuple[Driver]]) -> Select[tuple[Driver]]:
        return stmt.options(
            selectinload(Driver.customer_account),
            selectinload(Driver.organization),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc
