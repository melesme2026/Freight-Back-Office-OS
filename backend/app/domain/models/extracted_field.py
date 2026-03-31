from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.load_document import LoadDocument
    from app.domain.models.staff_user import StaffUser


class ExtractedField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        Index("ix_extracted_fields_organization_id", "organization_id"),
        Index("ix_extracted_fields_document_id", "document_id"),
        Index("ix_extracted_fields_load_id", "load_id"),
        Index("ix_extracted_fields_field_name", "field_name"),
        Index("ix_extracted_fields_confidence_score", "confidence_score"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("load_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    load_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loads.id", ondelete="SET NULL"),
        nullable=True,
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_value_number: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    field_value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    field_value_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    source_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_engine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_human_corrected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    corrected_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    corrected_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    document: Mapped["LoadDocument"] = relationship(
        back_populates="extracted_fields",
        lazy="selectin",
    )
    load: Mapped["Load | None"] = relationship(
        back_populates="extracted_fields",
        lazy="selectin",
    )
    corrected_by_staff_user: Mapped["StaffUser | None"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"ExtractedField(id={self.id!s}, field_name={self.field_name!r}, "
            f"confidence_score={self.confidence_score!r}, "
            f"is_human_corrected={self.is_human_corrected!r})"
        )