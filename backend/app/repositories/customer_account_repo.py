from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.models.customer_account import CustomerAccount


class CustomerAccountRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, customer_account: CustomerAccount) -> CustomerAccount:
        self.db.add(customer_account)
        self.db.flush()
        self.db.refresh(customer_account)
        return customer_account

    def get_by_id(self, customer_account_id: uuid.UUID) -> CustomerAccount | None:
        stmt = select(CustomerAccount).where(CustomerAccount.id == customer_account_id)
        return self.db.scalar(stmt)

    def get_by_account_code(
        self,
        account_code: str,
    ) -> CustomerAccount | None:
        stmt = select(CustomerAccount).where(CustomerAccount.account_code == account_code)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        status: CustomerAccountStatus | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[CustomerAccount], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(CustomerAccount)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(CustomerAccount)

        if organization_id is not None:
            stmt = stmt.where(CustomerAccount.organization_id == organization_id)
            count_stmt = count_stmt.where(CustomerAccount.organization_id == organization_id)

        if status is not None:
            stmt = stmt.where(CustomerAccount.status == status)
            count_stmt = count_stmt.where(CustomerAccount.status == status)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                CustomerAccount.account_name.ilike(pattern),
                CustomerAccount.account_code.ilike(pattern),
                CustomerAccount.primary_contact_name.ilike(pattern),
                CustomerAccount.primary_contact_email.ilike(pattern),
                CustomerAccount.billing_email.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(CustomerAccount.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, customer_account: CustomerAccount) -> CustomerAccount:
        self.db.add(customer_account)
        self.db.flush()
        self.db.refresh(customer_account)
        return customer_account

    def delete(self, customer_account: CustomerAccount) -> None:
        self.db.delete(customer_account)
        self.db.flush()