from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser


class SupportTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_organization_id", "organization_id"),
        Index("ix_support_tickets_customer_account_id", "customer_account_id"),
        Index("ix_support_tickets_driver_id", "driver_id"),
        Index("ix_support_tickets_load_id", "load_id"),
        Index("ix_support_tickets_status", "status"),
        Index("ix_support_tickets_priority", "priority"),
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
    assigned_to_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="normal")
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="support_tickets",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount | None"] = relationship(
        back_populates="support_tickets",
        lazy="selectin",
    )
    driver: Mapped["Driver | None"] = relationship(lazy="selectin")
    load: Mapped["Load | None"] = relationship(
        back_populates="support_tickets",
        lazy="selectin",
    )
    assigned_to: Mapped["StaffUser | None"] = relationship(
        back_populates="support_tickets_assigned",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"SupportTicket(id={self.id!s}, subject={self.subject!r}, "
            f"status={self.status!r}, priority={self.priority!r})"
        )