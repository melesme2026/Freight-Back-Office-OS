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
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser
    from app.domain.models.submission_event import SubmissionEvent
    from app.domain.models.submission_packet_document import SubmissionPacketDocument


class SubmissionPacket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_packets"
    __table_args__ = (
        Index("ix_submission_packets_organization_id", "organization_id"),
        Index("ix_submission_packets_load_id", "load_id"),
        Index("ix_submission_packets_status", "status"),
        Index("ix_submission_packets_sent_at", "sent_at"),
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
    packet_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_type: Mapped[str] = mapped_column(String(40), nullable=False, default="other", server_default="other")
    destination_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", server_default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sent_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    load: Mapped["Load"] = relationship(lazy="selectin")
    created_by_staff_user: Mapped["StaffUser | None"] = relationship(
        foreign_keys=[created_by_staff_user_id],
        lazy="selectin",
    )
    sent_by_staff_user: Mapped["StaffUser | None"] = relationship(
        foreign_keys=[sent_by_staff_user_id],
        lazy="selectin",
    )
    documents: Mapped[list["SubmissionPacketDocument"]] = relationship(
        back_populates="submission_packet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list["SubmissionEvent"]] = relationship(
        back_populates="submission_packet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
