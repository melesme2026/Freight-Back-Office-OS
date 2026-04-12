from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.extracted_field import ExtractedField
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser
    from app.domain.models.validation_issue import ValidationIssue


class LoadDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "load_documents"
    __table_args__ = (
        Index("ix_load_documents_organization_id", "organization_id"),
        Index("ix_load_documents_customer_account_id", "customer_account_id"),
        Index("ix_load_documents_driver_id", "driver_id"),
        Index("ix_load_documents_load_id", "load_id"),
        Index("ix_load_documents_uploaded_by_staff_user_id", "uploaded_by_staff_user_id"),
        Index("ix_load_documents_document_type", "document_type"),
        Index("ix_load_documents_processing_status", "processing_status"),
        Index("ix_load_documents_received_at", "received_at"),
        Index("ix_load_documents_file_hash_sha256", "file_hash_sha256", unique=True),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        nullable=False,
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

    source_channel: Mapped[Channel] = mapped_column(
        SqlEnum(
            Channel,
            name="channel",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=Channel.MANUAL,
        server_default=Channel.MANUAL.value,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SqlEnum(
            DocumentType,
            name="document_type",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentType.UNKNOWN,
        server_default=DocumentType.UNKNOWN.value,
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SqlEnum(
            ProcessingStatus,
            name="processing_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ProcessingStatus.PENDING,
        server_default=ProcessingStatus.PENDING.value,
    )
    classification_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ocr_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    uploaded_by_staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="load_documents",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount"] = relationship(
        lazy="selectin",
    )
    driver: Mapped["Driver | None"] = relationship(
        lazy="selectin",
    )
    load: Mapped["Load | None"] = relationship(
        back_populates="documents",
        lazy="selectin",
    )
    uploaded_by_staff_user: Mapped["StaffUser | None"] = relationship(
        lazy="selectin",
    )

    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="document",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "LoadDocument("
            f"id={self.id!s}, "
            f"document_type={self.document_type!r}, "
            f"processing_status={self.processing_status!r}, "
            f"storage_key={self.storage_key!r}"
            ")"
        )