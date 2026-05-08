from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.organization import Organization
    from app.domain.models.load_payment_record import LoadPaymentRecord


class FactoringCompany(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "factoring_companies"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_name", name="uq_factoring_companies_org_name"),
        Index("ix_factoring_companies_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_reserve_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("0"), server_default="0")
    default_fee_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("0"), server_default="0")

    organization: Mapped["Organization"] = relationship(back_populates="factoring_companies", lazy="selectin")
    payment_records: Mapped[list["LoadPaymentRecord"]] = relationship(back_populates="factoring_company", lazy="selectin")
