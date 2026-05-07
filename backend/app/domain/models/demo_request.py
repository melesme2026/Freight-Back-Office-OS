from __future__ import annotations

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class DemoRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "demo_requests"
    __table_args__ = (
        Index("ix_demo_requests_email", "email"),
        Index("ix_demo_requests_status", "status"),
        Index("ix_demo_requests_created_at", "created_at"),
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fleet_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new", server_default="new"
    )
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
