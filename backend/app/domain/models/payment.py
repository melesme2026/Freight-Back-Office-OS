from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.payment_status import PaymentStatus
from app.domain.enums.payment_provider import PaymentProvider
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice import BillingInvoice
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.ledger_entry import LedgerEntry
    from app.domain.models.organization import Organization
    from app.domain.models.payment_method import PaymentMethod
    from app.domain.models.staff_user import StaffUser


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_organization_id", "organization_id"),
        Index("ix_payments_customer_account_id", "customer_account_id"),
        Index("ix_payments_billing_invoice_id", "billing_invoice_id"),
        Index("ix_payments_payment_method_id", "payment_method_id"),
        Index("ix_payments_driver_id", "driver_id"),
        Index("ix_payments_recorded_by_staff_user_id", "recorded_by_staff_user_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_provider_payment_id", "provider_payment_id"),
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
    billing_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="SET NULL"),
        nullable=True,
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentProvider.MANUAL,
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="payments",
        lazy="selectin",
    )
    billing_invoice: Mapped["BillingInvoice | None"] = relationship(
        back_populates="payments",
        lazy="selectin",
    )
    payment_method: Mapped["PaymentMethod | None"] = relationship(
        back_populates="payments",
        lazy="selectin",
    )
    driver: Mapped["Driver | None"] = relationship(
        back_populates="payments",
        lazy="selectin",
    )
    recorded_by_staff_user: Mapped["StaffUser | None"] = relationship(
        back_populates="payments_recorded",
        lazy="selectin",
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="payment",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Payment(id={self.id!s}, status={self.status!r}, "
            f"amount={self.amount!r}, provider={self.provider!r})"
        )