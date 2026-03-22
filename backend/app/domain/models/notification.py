from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.channel import Channel
from app.domain.enums.notification_status import NotificationStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_organization_id", "organization_id"),
        Index("ix_notifications_customer_account_id", "customer_account_id"),
        Index("ix_notifications_driver_id", "driver_id"),
        Index("ix_notifications_load_id", "load_id"),
        Index("ix_notifications_channel", "channel"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_provider_message_id", "provider_message_id"),
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
    created_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel: Mapped[Channel] = mapped_column(
        String(50),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        String(50),
        nullable=False,
        default=NotificationStatus.QUEUED,
    )
    sent_at: Mapped[str | None] = mapped_column(nullable=True)
    delivered_at: Mapped[str | None] = mapped_column(nullable=True)
    failed_at: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(
        back_populates="notifications",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount | None"] = relationship(
        back_populates="notifications",
        lazy="selectin",
    )
    driver: Mapped["Driver | None"] = relationship(
        back_populates="notifications",
        lazy="selectin",
    )
    load: Mapped["Load | None"] = relationship(
        back_populates="notifications",
        lazy="selectin",
    )
    created_by_staff_user: Mapped["StaffUser | None"] = relationship(
        back_populates="notifications_created",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Notification(id={self.id!s}, channel={self.channel!r}, "
            f"status={self.status!r}, direction={self.direction!r})"
        )