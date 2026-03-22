from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.load import Load
    from app.domain.models.organization import Organization


class Broker(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brokers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "name",
            "mc_number",
            name="uq_brokers_org_name_mc_number",
        ),
        Index("ix_brokers_organization_id", "organization_id"),
        Index("ix_brokers_name", "name"),
        Index("ix_brokers_mc_number", "mc_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mc_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(
        back_populates="brokers",
        lazy="selectin",
    )
    loads: Mapped[list["Load"]] = relationship(
        back_populates="broker",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Broker(id={self.id!s}, name={self.name!r}, "
            f"mc_number={self.mc_number!r})"
        )