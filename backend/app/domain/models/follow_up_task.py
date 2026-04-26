from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.follow_up_task import FollowUpTaskPriority, FollowUpTaskStatus, FollowUpTaskType
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.load_payment_record import LoadPaymentRecord
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser
    from app.domain.models.submission_packet import SubmissionPacket


class FollowUpTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        Index("ix_follow_up_tasks_organization_id", "organization_id"),
        Index("ix_follow_up_tasks_load_id", "load_id"),
        Index("ix_follow_up_tasks_submission_packet_id", "submission_packet_id"),
        Index("ix_follow_up_tasks_payment_record_id", "payment_record_id"),
        Index("ix_follow_up_tasks_status", "status"),
        Index("ix_follow_up_tasks_priority", "priority"),
        Index("ix_follow_up_tasks_due_at", "due_at"),
        Index("ix_follow_up_tasks_task_type", "task_type"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    load_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("loads.id", ondelete="CASCADE"), nullable=False)
    submission_packet_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("submission_packets.id", ondelete="SET NULL"), nullable=True)
    payment_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("load_payment_records.id", ondelete="SET NULL"), nullable=True)

    task_type: Mapped[FollowUpTaskType] = mapped_column(
        SqlEnum(
            FollowUpTaskType,
            name="follow_up_task_type",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[FollowUpTaskStatus] = mapped_column(
        SqlEnum(
            FollowUpTaskStatus,
            name="follow_up_task_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=FollowUpTaskStatus.OPEN,
        server_default=FollowUpTaskStatus.OPEN.value,
    )
    priority: Mapped[FollowUpTaskPriority] = mapped_column(
        SqlEnum(
            FollowUpTaskPriority,
            name="follow_up_task_priority",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=FollowUpTaskPriority.NORMAL,
        server_default=FollowUpTaskPriority.NORMAL.value,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff_users.id", ondelete="SET NULL"), nullable=True)
    created_by_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    organization: Mapped["Organization"] = relationship(back_populates="follow_up_tasks", lazy="selectin")
    load: Mapped["Load"] = relationship(back_populates="follow_up_tasks", lazy="selectin")
    submission_packet: Mapped["SubmissionPacket | None"] = relationship(lazy="selectin")
    payment_record: Mapped["LoadPaymentRecord | None"] = relationship(lazy="selectin")
    assigned_to_staff_user: Mapped["StaffUser | None"] = relationship(foreign_keys=[assigned_to_staff_user_id], lazy="selectin")
