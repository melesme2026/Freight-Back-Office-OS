from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.subscription import Subscription
    from app.domain.models.billing_invoice_line import BillingInvoiceLine


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_organization_id", "organization_id"),
        Index("ix_usage_records_customer_account_id", "customer_account_id"),
        Index("ix_usage_records_subscription_id", "subscription_id"),
        Index("ix_usage_records_load_id", "load_id"),
        Index("ix_usage_records_usage_type", "usage_type"),
        Index("ix_usage_records_usage_date", "usage_date"),
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
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
    )
    load_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loads.id", ondelete="SET NULL"),
        nullable=True,
    )

    usage_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="usage_records",
        lazy="selectin",
    )
    subscription: Mapped["Subscription"] = relationship(
        back_populates="usage_records",
        lazy="selectin",
    )
    driver: Mapped["Driver | None"] = relationship(
        back_populates="usage_records",
        lazy="selectin",
    )
    load: Mapped["Load | None"] = relationship(
        back_populates="usage_records",
        lazy="selectin",
    )
    invoice_lines: Mapped[list["BillingInvoiceLine"]] = relationship(
        back_populates="usage_record",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"UsageRecord(id={self.id!s}, usage_type={self.usage_type!r}, "
            f"quantity={self.quantity!r}, usage_date={self.usage_date!r})"
        )