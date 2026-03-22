from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice import BillingInvoice
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment


class LedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_entries_organization_id", "organization_id"),
        Index("ix_ledger_entries_customer_account_id", "customer_account_id"),
        Index("ix_ledger_entries_billing_invoice_id", "billing_invoice_id"),
        Index("ix_ledger_entries_payment_id", "payment_id"),
        Index("ix_ledger_entries_entry_type", "entry_type"),
        Index("ix_ledger_entries_entry_date", "entry_date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    billing_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount | None"] = relationship(
        back_populates="ledger_entries",
        lazy="selectin",
    )
    billing_invoice: Mapped["BillingInvoice | None"] = relationship(
        back_populates="ledger_entries",
        lazy="selectin",
    )
    payment: Mapped["Payment | None"] = relationship(
        back_populates="ledger_entries",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"LedgerEntry(id={self.id!s}, entry_type={self.entry_type!r}, "
            f"amount={self.amount!r}, entry_date={self.entry_date!r})"
        )