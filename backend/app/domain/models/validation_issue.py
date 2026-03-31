from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.load_document import LoadDocument
    from app.domain.models.staff_user import StaffUser


class ValidationIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "validation_issues"
    __table_args__ = (
        Index("ix_validation_issues_organization_id", "organization_id"),
        Index("ix_validation_issues_load_id", "load_id"),
        Index("ix_validation_issues_document_id", "document_id"),
        Index("ix_validation_issues_rule_code", "rule_code"),
        Index("ix_validation_issues_severity", "severity"),
        Index("ix_validation_issues_is_resolved", "is_resolved"),
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
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("load_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[ValidationSeverity] = mapped_column(
        SqlEnum(
            ValidationSeverity,
            name="validation_severity",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    resolved_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    load: Mapped["Load"] = relationship(
        back_populates="validation_issues",
        lazy="selectin",
    )
    document: Mapped["LoadDocument | None"] = relationship(
        back_populates="validation_issues",
        lazy="selectin",
    )
    resolved_by_user: Mapped["StaffUser | None"] = relationship(
        back_populates="validation_issues_resolved",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"ValidationIssue(id={self.id!s}, rule_code={self.rule_code!r}, "
            f"severity={self.severity!r}, is_resolved={self.is_resolved!r})"
        )