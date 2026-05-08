from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.domain.models.organization import Organization


class AccountingExportMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Lightweight accounting category labels used on CSV exports."""

    __tablename__ = "accounting_export_mappings"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_accounting_export_mappings_org"),
        Index("ix_accounting_export_mappings_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    accounting_category: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Freight Operations",
        server_default="Freight Operations",
    )
    revenue_category: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Freight Revenue",
        server_default="Freight Revenue",
    )
    factoring_category: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Factoring",
        server_default="Factoring",
    )
    settlement_category: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Settlements",
        server_default="Settlements",
    )
    payment_category: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="Customer Payments",
        server_default="Customer Payments",
    )

    organization: Mapped[Organization] = relationship(lazy="selectin")


class AccountingIntegrationSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Safe QuickBooks foundation without token storage or bidirectional sync."""

    __tablename__ = "accounting_integration_settings"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_accounting_integration_settings_org"),
        Index("ix_accounting_integration_settings_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="quickbooks",
        server_default="quickbooks",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    realm_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_export_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="csv",
        server_default="csv",
    )
    sync_mode: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="export_ready",
        server_default="export_ready",
    )
    last_export_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(lazy="selectin")
