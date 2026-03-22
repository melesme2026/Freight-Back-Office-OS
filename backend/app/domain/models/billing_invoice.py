from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice_line import BillingInvoiceLine
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.ledger_entry import LedgerEntry
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment
    from app.domain.models.subscription import Subscription


class BillingInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "invoice_number",
            name="uq_billing_invoices_org_invoice_number",
        ),
        Index("ix_billing_invoices_customer_account_id", "customer_account_id"),
        Index("ix_billing_invoices_subscription_id", "subscription_id"),
        Index("ix_billing_invoices_status", "status"),
        Index("ix_billing_invoices_due_at", "due_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    amount_due: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="billing_invoices",
        lazy="selectin",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="billing_invoices",
        lazy="selectin",
    )
    lines: Mapped[list["BillingInvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="billing_invoice",
        lazy="selectin",
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="billing_invoice",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"BillingInvoice(id={self.id!s}, invoice_number={self.invoice_number!r}, "
            f"status={self.status!r}, total_amount={self.total_amount!r})"
        )