from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.payment_status import PaymentStatus
from app.domain.models.payment import Payment


class PaymentRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        return self.db.scalar(stmt)

    def get_by_provider_payment_id(
        self,
        provider_payment_id: str,
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        billing_invoice_id: uuid.UUID | None = None,
        payment_method_id: uuid.UUID | None = None,
        status: PaymentStatus | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Payment], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(Payment)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Payment)

        if organization_id is not None:
            stmt = stmt.where(Payment.organization_id == organization_id)
            count_stmt = count_stmt.where(Payment.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Payment.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(Payment.customer_account_id == customer_account_id)

        if billing_invoice_id is not None:
            stmt = stmt.where(Payment.billing_invoice_id == billing_invoice_id)
            count_stmt = count_stmt.where(Payment.billing_invoice_id == billing_invoice_id)

        if payment_method_id is not None:
            stmt = stmt.where(Payment.payment_method_id == payment_method_id)
            count_stmt = count_stmt.where(Payment.payment_method_id == payment_method_id)

        if status is not None:
            stmt = stmt.where(Payment.status == status)
            count_stmt = count_stmt.where(Payment.status == status)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def delete(self, payment: Payment) -> None:
        self.db.delete(payment)
        self.db.flush()