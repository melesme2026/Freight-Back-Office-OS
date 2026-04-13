from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

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

    def get_by_id(
        self,
        payment_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> Payment | None:
        normalized_payment_id = self._normalize_uuid(payment_id, field_name="payment_id")

        stmt = select(Payment).where(Payment.id == normalized_payment_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_provider_payment_id(
        self,
        provider_payment_id: str,
        *,
        include_related: bool = False,
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        billing_invoice_id: uuid.UUID | str | None = None,
        payment_method_id: uuid.UUID | str | None = None,
        driver_id: uuid.UUID | str | None = None,
        status: PaymentStatus | str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[Payment], int]:
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
        normalized_billing_invoice_id = (
            self._normalize_uuid(billing_invoice_id, field_name="billing_invoice_id")
            if billing_invoice_id is not None
            else None
        )
        normalized_payment_method_id = (
            self._normalize_uuid(payment_method_id, field_name="payment_method_id")
            if payment_method_id is not None
            else None
        )
        normalized_driver_id = (
            self._normalize_uuid(driver_id, field_name="driver_id")
            if driver_id is not None
            else None
        )
        normalized_status = self._normalize_status(status)

        stmt = select(Payment)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Payment)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(Payment.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(Payment.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Payment.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(Payment.customer_account_id == normalized_customer_account_id)

        if normalized_billing_invoice_id is not None:
            stmt = stmt.where(Payment.billing_invoice_id == normalized_billing_invoice_id)
            count_stmt = count_stmt.where(Payment.billing_invoice_id == normalized_billing_invoice_id)

        if normalized_payment_method_id is not None:
            stmt = stmt.where(Payment.payment_method_id == normalized_payment_method_id)
            count_stmt = count_stmt.where(Payment.payment_method_id == normalized_payment_method_id)

        if normalized_driver_id is not None:
            stmt = stmt.where(Payment.driver_id == normalized_driver_id)
            count_stmt = count_stmt.where(Payment.driver_id == normalized_driver_id)

        if normalized_status is not None:
            stmt = stmt.where(Payment.status == normalized_status)
            count_stmt = count_stmt.where(Payment.status == normalized_status)

        total = int(self.db.scalar(count_stmt) or 0)

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

    def _apply_related(self, stmt: Select[tuple[Payment]]) -> Select[tuple[Payment]]:
        return stmt.options(
            selectinload(Payment.customer_account),
            selectinload(Payment.billing_invoice),
            selectinload(Payment.payment_method),
            selectinload(Payment.driver),
            selectinload(Payment.recorded_by_staff_user),
            selectinload(Payment.ledger_entries),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    def _normalize_status(self, value: PaymentStatus | str | None) -> PaymentStatus | None:
        if value is None:
            return None

        if isinstance(value, PaymentStatus):
            return value

        normalized = str(value).strip().lower()

        for status in PaymentStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValueError(f"Invalid status: {value}")
