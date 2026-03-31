from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.payment_provider import PaymentProvider
from app.domain.models.payment_method import PaymentMethod


class PaymentMethodRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payment_method: PaymentMethod) -> PaymentMethod:
        self.db.add(payment_method)
        self.db.flush()
        self.db.refresh(payment_method)
        return payment_method

    def get_by_id(self, payment_method_id: uuid.UUID) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(PaymentMethod.id == payment_method_id)
        return self.db.scalar(stmt)

    def get_by_provider_payment_method_id(
        self,
        *,
        customer_account_id: uuid.UUID,
        provider_payment_method_id: str,
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.customer_account_id == customer_account_id,
            PaymentMethod.provider_payment_method_id == provider_payment_method_id,
        )
        return self.db.scalar(stmt)

    def get_default_for_customer_account(
        self,
        customer_account_id: uuid.UUID,
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.customer_account_id == customer_account_id,
            PaymentMethod.is_default.is_(True),
            PaymentMethod.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        provider: PaymentProvider | None = None,
        is_default: bool | None = None,
        is_active: bool | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[PaymentMethod], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(PaymentMethod)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(PaymentMethod)

        if organization_id is not None:
            stmt = stmt.where(PaymentMethod.organization_id == organization_id)
            count_stmt = count_stmt.where(PaymentMethod.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(PaymentMethod.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                PaymentMethod.customer_account_id == customer_account_id
            )

        if provider is not None:
            stmt = stmt.where(PaymentMethod.provider == provider)
            count_stmt = count_stmt.where(PaymentMethod.provider == provider)

        if is_default is not None:
            stmt = stmt.where(PaymentMethod.is_default == is_default)
            count_stmt = count_stmt.where(PaymentMethod.is_default == is_default)

        if is_active is not None:
            stmt = stmt.where(PaymentMethod.is_active == is_active)
            count_stmt = count_stmt.where(PaymentMethod.is_active == is_active)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(
                PaymentMethod.is_default.desc(),
                PaymentMethod.created_at.desc(),
            )
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def clear_default_for_customer_account(
        self,
        customer_account_id: uuid.UUID,
    ) -> int:
        items, _ = self.list(
            customer_account_id=customer_account_id,
            is_default=True,
            page=1,
            page_size=100,
        )
        for item in items:
            item.is_default = False
            self.db.add(item)
        self.db.flush()
        return len(items)

    def update(self, payment_method: PaymentMethod) -> PaymentMethod:
        self.db.add(payment_method)
        self.db.flush()
        self.db.refresh(payment_method)
        return payment_method

    def delete(self, payment_method: PaymentMethod) -> None:
        self.db.delete(payment_method)
        self.db.flush()