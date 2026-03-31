from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

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

    def get_by_id(self, driver_id: uuid.UUID) -> Driver | None:
        stmt = select(Driver).where(Driver.id == driver_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Driver], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(Driver)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Driver)

        if organization_id is not None:
            stmt = stmt.where(Driver.organization_id == organization_id)
            count_stmt = count_stmt.where(Driver.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Driver.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(Driver.customer_account_id == customer_account_id)

        if is_active is not None:
            stmt = stmt.where(Driver.is_active == is_active)
            count_stmt = count_stmt.where(Driver.is_active == is_active)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Driver.full_name.ilike(pattern),
                Driver.phone.ilike(pattern),
                Driver.email.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = stmt.order_by(Driver.created_at.desc()).offset(offset).limit(normalized_page_size)

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