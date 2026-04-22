from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.role import Role
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.notification import Notification
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment
    from app.domain.models.support_ticket import SupportTicket
    from app.domain.models.validation_issue import ValidationIssue
    from app.domain.models.workflow_event import WorkflowEvent


class StaffUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_users"
    __table_args__ = (
        Index("ix_staff_users_organization_id", "organization_id"),
        Index("ix_staff_users_role", "role"),
        Index("ix_staff_users_is_active", "is_active"),
        Index("ix_staff_users_org_email", "organization_id", "email", unique=True),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(
        SqlEnum(
            Role,
            name="role",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=Role.OPS_AGENT,
        server_default=Role.OPS_AGENT.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="staff_users",
        lazy="selectin",
    )

    reviewed_loads: Mapped[list["Load"]] = relationship(
        back_populates="last_reviewed_by_user",
        foreign_keys="Load.last_reviewed_by",
        lazy="selectin",
    )
    follow_up_owned_loads: Mapped[list["Load"]] = relationship(
        back_populates="follow_up_owner",
        foreign_keys="Load.follow_up_owner_id",
        lazy="selectin",
    )
    validation_issues_resolved: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="resolved_by_user",
        lazy="selectin",
    )
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="actor_staff_user",
        lazy="selectin",
    )
    support_tickets_assigned: Mapped[list["SupportTicket"]] = relationship(
        back_populates="assigned_to",
        lazy="selectin",
    )
    notifications_created: Mapped[list["Notification"]] = relationship(
        back_populates="created_by_staff_user",
        lazy="selectin",
    )
    payments_recorded: Mapped[list["Payment"]] = relationship(
        back_populates="recorded_by_staff_user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"StaffUser(id={self.id!s}, email={self.email!r}, "
            f"role={self.role!r}, is_active={self.is_active!r})"
        )
