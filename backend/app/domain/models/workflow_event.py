from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.enums.load_status import LoadStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser


class WorkflowEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        Index("ix_workflow_events_organization_id", "organization_id"),
        Index("ix_workflow_events_load_id", "load_id"),
        Index("ix_workflow_events_event_type", "event_type"),
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
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    old_status: Mapped[LoadStatus | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[LoadStatus | None] = mapped_column(String(50), nullable=True)
    event_payload: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    actor_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_type: Mapped[AuditActorType] = mapped_column(
        String(50),
        nullable=False,
        default=AuditActorType.SYSTEM,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="workflow_events",
        lazy="selectin",
    )
    load: Mapped["Load"] = relationship(
        back_populates="workflow_events",
        lazy="selectin",
    )
    actor_staff_user: Mapped["StaffUser | None"] = relationship(
        back_populates="workflow_events",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"WorkflowEvent(id={self.id!s}, event_type={self.event_type!r}, "
            f"old_status={self.old_status!r}, new_status={self.new_status!r}, "
            f"actor_type={self.actor_type!r})"
        )