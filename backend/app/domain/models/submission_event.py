from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser
    from app.domain.models.submission_packet import SubmissionPacket


class SubmissionEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_events"
    __table_args__ = (
        Index("ix_submission_events_organization_id", "organization_id"),
        Index("ix_submission_events_load_id", "load_id"),
        Index("ix_submission_events_submission_packet_id", "submission_packet_id"),
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
    submission_packet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submission_packets.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    load: Mapped["Load"] = relationship(lazy="selectin")
    submission_packet: Mapped["SubmissionPacket | None"] = relationship(back_populates="events", lazy="selectin")
    created_by_staff_user: Mapped["StaffUser | None"] = relationship(lazy="selectin")
