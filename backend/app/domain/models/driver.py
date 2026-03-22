from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.load import Load
    from app.domain.models.notification import Notification
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment
    from app.domain.models.usage_record import UsageRecord


class Driver(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drivers"
    __table_args__ = (
        Index("ix_drivers_organization_id", "organization_id"),
        Index("ix_drivers_customer_account_id", "customer_account_id"),
        Index("ix_drivers_phone", "phone"),
        Index("ix_drivers_is_active", "is_active"),
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
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="drivers",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount | None"] = relationship(
        back_populates="drivers",
        lazy="selectin",
    )
    loads: Mapped[list["Load"]] = relationship(
        back_populates="driver",
        lazy="selectin",
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="driver",
        lazy="selectin",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="driver",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="driver",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Driver(id={self.id!s}, full_name={self.full_name!r}, "
            f"phone={self.phone!r}, is_active={self.is_active!r})"
        )