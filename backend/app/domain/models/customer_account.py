from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.billing_invoice import BillingInvoice
    from app.domain.models.driver import Driver
    from app.domain.models.ledger_entry import LedgerEntry
    from app.domain.models.load import Load
    from app.domain.models.notification import Notification
    from app.domain.models.onboarding_checklist import OnboardingChecklist
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment
    from app.domain.models.payment_method import PaymentMethod
    from app.domain.models.referral import Referral
    from app.domain.models.subscription import Subscription
    from app.domain.models.support_ticket import SupportTicket
    from app.domain.models.usage_record import UsageRecord


class CustomerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_accounts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "account_name",
            name="uq_customer_accounts_org_account_name",
        ),
        Index("ix_customer_accounts_organization_id", "organization_id"),
        Index("ix_customer_accounts_status", "status"),
        Index("ix_customer_accounts_account_code", "account_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
    )
    status: Mapped[CustomerAccountStatus] = mapped_column(
        SqlEnum(
            CustomerAccountStatus,
            name="customer_account_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CustomerAccountStatus.PROSPECT,
        server_default=CustomerAccountStatus.PROSPECT.value,
    )
    primary_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(
        back_populates="customer_accounts",
        lazy="selectin",
    )
    onboarding_checklist: Mapped["OnboardingChecklist | None"] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    referrals: Mapped[list["Referral"]] = relationship(
        back_populates="customer_account",
        lazy="selectin",
    )
    drivers: Mapped[list["Driver"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    loads: Mapped[list["Load"]] = relationship(
        back_populates="customer_account",
        lazy="selectin",
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    billing_invoices: Mapped[list["BillingInvoice"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="customer_account",
        lazy="selectin",
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="customer_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="customer_account",
        lazy="selectin",
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer_account",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"CustomerAccount(id={self.id!s}, account_name={self.account_name!r}, "
            f"status={self.status!r})"
        )