from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

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

    def get_by_id(
        self,
        customer_account_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> CustomerAccount | None:
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )

        stmt = select(CustomerAccount).where(CustomerAccount.id == normalized_customer_account_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_account_code(
        self,
        account_code: str,
        *,
        include_related: bool = False,
    ) -> CustomerAccount | None:
        stmt = select(CustomerAccount).where(CustomerAccount.account_code == account_code)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        status: CustomerAccountStatus | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[CustomerAccount], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_search = search.strip() if search else None

        stmt = select(CustomerAccount)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(CustomerAccount)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(CustomerAccount.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(CustomerAccount.organization_id == normalized_organization_id)

        if status is not None:
            stmt = stmt.where(CustomerAccount.status == status)
            count_stmt = count_stmt.where(CustomerAccount.status == status)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                CustomerAccount.account_name.ilike(pattern),
                CustomerAccount.account_code.ilike(pattern),
                CustomerAccount.primary_contact_name.ilike(pattern),
                CustomerAccount.primary_contact_email.ilike(pattern),
                CustomerAccount.primary_contact_phone.ilike(pattern),
                CustomerAccount.billing_email.ilike(pattern),
                CustomerAccount.notes.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

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

    def _apply_related(
        self,
        stmt: Select[tuple[CustomerAccount]],
    ) -> Select[tuple[CustomerAccount]]:
        return stmt.options(
            selectinload(CustomerAccount.organization),
            selectinload(CustomerAccount.drivers),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc