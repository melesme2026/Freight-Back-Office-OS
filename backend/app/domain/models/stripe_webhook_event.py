from __future__ import annotations

import uuid
from datetime import datetime

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class StripeWebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stripe_webhook_events"
    __table_args__ = (
        Index("ix_stripe_webhook_events_stripe_event_id", "stripe_event_id", unique=True),
        Index("ix_stripe_webhook_events_event_type", "event_type"),
    )

    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="processed",
        server_default="processed",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
