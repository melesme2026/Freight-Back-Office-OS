from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.organization import Organization


class Referral(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("ix_referrals_organization_id", "organization_id"),
        Index("ix_referrals_customer_account_id", "customer_account_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    referred_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    referred_by_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referred_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(
        back_populates="referrals",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount | None"] = relationship(
        back_populates="referrals",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Referral(id={self.id!s}, referred_by_name={self.referred_by_name!r}, "
            f"customer_account_id={self.customer_account_id!s})"
        )
        