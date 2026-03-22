from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.organization import Organization


class ApiClient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_clients"
    __table_args__ = (
        Index("ix_api_clients_organization_id", "organization_id"),
        Index("ix_api_clients_is_active", "is_active"),
        Index("ix_api_clients_client_key", "client_key", unique=True),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    client_secret_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    allowed_scopes_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="api_clients",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"ApiClient(id={self.id!s}, name={self.name!r}, "
            f"client_key={self.client_key!r}, is_active={self.is_active!r})"
        )