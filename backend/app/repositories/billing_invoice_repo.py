from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.models.billing_invoice import BillingInvoice


class BillingInvoiceRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, billing_invoice: BillingInvoice) -> BillingInvoice:
        self.db.add(billing_invoice)
        self.db.flush()
        self.db.refresh(billing_invoice)
        return billing_invoice

    def get_by_id(
        self,
        invoice_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> BillingInvoice | None:
        normalized_invoice_id = self._normalize_uuid(invoice_id, field_name="invoice_id")

        stmt = select(BillingInvoice).where(BillingInvoice.id == normalized_invoice_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_invoice_number(
        self,
        *,
        organization_id: uuid.UUID | str,
        invoice_number: str,
        include_related: bool = False,
    ) -> BillingInvoice | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )

        stmt = select(BillingInvoice).where(
            BillingInvoice.organization_id == normalized_organization_id,
            BillingInvoice.invoice_number == invoice_number,
        )

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        subscription_id: uuid.UUID | str | None = None,
        status: InvoiceStatus | str | None = None,
        due_before: datetime | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[BillingInvoice], int]:
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
        normalized_subscription_id = (
            self._normalize_uuid(subscription_id, field_name="subscription_id")
            if subscription_id is not None
            else None
        )
        normalized_status = self._normalize_status(status)

        stmt = select(BillingInvoice)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(BillingInvoice)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(BillingInvoice.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(BillingInvoice.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(BillingInvoice.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                BillingInvoice.customer_account_id == normalized_customer_account_id
            )

        if normalized_subscription_id is not None:
            stmt = stmt.where(BillingInvoice.subscription_id == normalized_subscription_id)
            count_stmt = count_stmt.where(BillingInvoice.subscription_id == normalized_subscription_id)

        if normalized_status is not None:
            stmt = stmt.where(BillingInvoice.status == normalized_status)
            count_stmt = count_stmt.where(BillingInvoice.status == normalized_status)

        if due_before is not None:
            stmt = stmt.where(BillingInvoice.due_at.is_not(None))
            stmt = stmt.where(BillingInvoice.due_at <= due_before)
            count_stmt = count_stmt.where(BillingInvoice.due_at.is_not(None))
            count_stmt = count_stmt.where(BillingInvoice.due_at <= due_before)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(BillingInvoice.issued_at.desc(), BillingInvoice.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
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

    def _apply_related(
        self,
        stmt: Select[tuple[BillingInvoice]],
    ) -> Select[tuple[BillingInvoice]]:
        return stmt.options(
            selectinload(BillingInvoice.customer_account),
            selectinload(BillingInvoice.subscription),
            selectinload(BillingInvoice.lines),
            selectinload(BillingInvoice.payments),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    def _normalize_status(self, value: InvoiceStatus | str | None) -> InvoiceStatus | None:
        if value is None:
            return None

        if isinstance(value, InvoiceStatus):
            return value

        normalized = str(value).strip().lower()

        for status in InvoiceStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValueError(f"Invalid status: {value}")