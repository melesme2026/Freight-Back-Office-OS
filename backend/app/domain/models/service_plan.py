from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.billing_cycle import BillingCycle
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.organization import Organization
    from app.domain.models.subscription import Subscription


class ServicePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_plans"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_service_plans_org_code"),
        Index("ix_service_plans_is_active", "is_active"),
        Index("ix_service_plans_organization_id", "organization_id"),
        Index("ix_service_plans_billing_cycle", "billing_cycle"),  # added for filtering
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    billing_cycle: Mapped[BillingCycle] = mapped_column(
        SqlEnum(
            BillingCycle,
            name="billing_cycle",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=BillingCycle.MONTHLY,
        server_default=BillingCycle.MONTHLY.value,
    )

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        server_default="USD",
    )

    per_load_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=None,
    )

    per_driver_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=None,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="service_plans",
        lazy="selectin",
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="service_plan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"ServicePlan(id={self.id!s}, code={self.code!r}, "
            f"billing_cycle={self.billing_cycle!r}, is_active={self.is_active!r})"
        )