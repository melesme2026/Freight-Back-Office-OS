from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.load_document import LoadDocument
    from app.domain.models.submission_packet import SubmissionPacket


class SubmissionPacketDocument(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "submission_packet_documents"
    __table_args__ = (
        Index("ix_submission_packet_documents_submission_packet_id", "submission_packet_id"),
        Index("ix_submission_packet_documents_document_id", "document_id"),
    )

    submission_packet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submission_packets.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("load_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    filename_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    submission_packet: Mapped["SubmissionPacket"] = relationship(back_populates="documents", lazy="selectin")
    document: Mapped["LoadDocument"] = relationship(lazy="selectin")
