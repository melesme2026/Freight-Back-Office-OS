from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice import BillingInvoice
    from app.domain.models.usage_record import UsageRecord


class BillingInvoiceLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "billing_invoice_lines"
    __table_args__ = (
        Index("ix_billing_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_billing_invoice_lines_usage_record_id", "usage_record_id"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usage_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    line_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default="1",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    invoice: Mapped["BillingInvoice"] = relationship(
        back_populates="lines",
        lazy="selectin",
    )
    usage_record: Mapped["UsageRecord | None"] = relationship(
        back_populates="invoice_lines",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"BillingInvoiceLine(id={self.id!s}, line_type={self.line_type!r}, "
            f"quantity={self.quantity!r}, line_total={self.line_total!r})"
        )