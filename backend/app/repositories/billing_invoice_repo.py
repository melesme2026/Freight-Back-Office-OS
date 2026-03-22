from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.models.billing_invoice import BillingInvoice


class BillingInvoiceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, billing_invoice: BillingInvoice) -> BillingInvoice:
        self.db.add(billing_invoice)
        self.db.flush()
        self.db.refresh(billing_invoice)
        return billing_invoice

    def get_by_id(self, invoice_id: uuid.UUID) -> BillingInvoice | None:
        stmt = select(BillingInvoice).where(BillingInvoice.id == invoice_id)
        return self.db.scalar(stmt)

    def get_by_invoice_number(
        self,
        *,
        organization_id: uuid.UUID,
        invoice_number: str,
    ) -> BillingInvoice | None:
        stmt = select(BillingInvoice).where(
            BillingInvoice.organization_id == organization_id,
            BillingInvoice.invoice_number == invoice_number,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        subscription_id: uuid.UUID | None = None,
        status: InvoiceStatus | None = None,
        due_before: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[BillingInvoice], int]:
        stmt = select(BillingInvoice)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(BillingInvoice)

        if organization_id is not None:
            stmt = stmt.where(BillingInvoice.organization_id == organization_id)
            count_stmt = count_stmt.where(BillingInvoice.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(BillingInvoice.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                BillingInvoice.customer_account_id == customer_account_id
            )

        if subscription_id is not None:
            stmt = stmt.where(BillingInvoice.subscription_id == subscription_id)
            count_stmt = count_stmt.where(BillingInvoice.subscription_id == subscription_id)

        if status is not None:
            stmt = stmt.where(BillingInvoice.status == status)
            count_stmt = count_stmt.where(BillingInvoice.status == status)

        if due_before is not None:
            stmt = stmt.where(BillingInvoice.due_at.is_not(None))
            stmt = stmt.where(BillingInvoice.due_at <= due_before)
            count_stmt = count_stmt.where(BillingInvoice.due_at.is_not(None))
            count_stmt = count_stmt.where(BillingInvoice.due_at <= due_before)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(BillingInvoice.issued_at.desc(), BillingInvoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, billing_invoice: BillingInvoice) -> BillingInvoice:
        self.db.add(billing_invoice)
        self.db.flush()
        self.db.refresh(billing_invoice)
        return billing_invoice

    def delete(self, billing_invoice: BillingInvoice) -> None:
        self.db.delete(billing_invoice)
        self.db.flush()