from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.subscription_status import SubscriptionStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice import BillingInvoice
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.organization import Organization
    from app.domain.models.service_plan import ServicePlan
    from app.domain.models.usage_record import UsageRecord


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_organization_id", "organization_id"),
        Index("ix_subscriptions_customer_account_id", "customer_account_id"),
        Index("ix_subscriptions_service_plan_id", "service_plan_id"),
        Index("ix_subscriptions_status", "status"),
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
    service_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        SqlEnum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="subscriptions",
        lazy="selectin",
    )
    service_plan: Mapped["ServicePlan"] = relationship(
        back_populates="subscriptions",
        lazy="selectin",
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    billing_invoices: Mapped[list["BillingInvoice"]] = relationship(
        back_populates="subscription",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Subscription(id={self.id!s}, status={self.status!r}, "
            f"customer_account_id={self.customer_account_id!s}, "
            f"service_plan_id={self.service_plan_id!s})"
        )