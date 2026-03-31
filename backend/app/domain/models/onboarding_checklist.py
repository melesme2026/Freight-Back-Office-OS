from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.onboarding_status import OnboardingStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.organization import Organization


class OnboardingChecklist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_checklists"
    __table_args__ = (
        Index("ix_onboarding_checklists_organization_id", "organization_id"),
        Index("ix_onboarding_checklists_status", "status"),
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
        unique=True,
    )
    status: Mapped[OnboardingStatus] = mapped_column(
        SqlEnum(
            OnboardingStatus,
            name="onboarding_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=OnboardingStatus.NOT_STARTED,
        server_default=OnboardingStatus.NOT_STARTED.value,
    )
    documents_received: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    pricing_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    payment_method_added: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    driver_profiles_created: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    channel_connected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    go_live_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="onboarding_checklist",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"OnboardingChecklist(id={self.id!s}, "
            f"customer_account_id={self.customer_account_id!s}, "
            f"status={self.status!r})"
        )