from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser


class LoadPaymentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "load_payment_records"
    __table_args__ = (
        UniqueConstraint("load_id", name="uq_load_payment_records_load_id"),
        Index("ix_load_payment_records_organization_id", "organization_id"),
        Index("ix_load_payment_records_load_id", "load_id"),
        Index("ix_load_payment_records_payment_status", "payment_status"),
        Index("ix_load_payment_records_paid_date", "paid_date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loads.id", ondelete="CASCADE"),
        nullable=False,
    )

    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0")
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0")
    amount_received: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")

    payment_status: Mapped[LoadPaymentStatus] = mapped_column(
        SqlEnum(
            LoadPaymentStatus,
            name="load_payment_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LoadPaymentStatus.NOT_SUBMITTED,
        server_default=LoadPaymentStatus.NOT_SUBMITTED.value,
    )

    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    factoring_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    factor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    advance_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    advance_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    factoring_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    reserve_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    reserve_paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0")
    reserve_paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deduction_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    short_paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(back_populates="load_payment_records", lazy="selectin")
    load: Mapped["Load"] = relationship(back_populates="payment_record", lazy="selectin")
    created_by_staff_user: Mapped["StaffUser | None"] = relationship(foreign_keys=[created_by_staff_user_id], lazy="selectin")
    updated_by_staff_user: Mapped["StaffUser | None"] = relationship(foreign_keys=[updated_by_staff_user_id], lazy="selectin")
