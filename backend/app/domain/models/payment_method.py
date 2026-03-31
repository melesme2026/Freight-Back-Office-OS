from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.payment_method_type import PaymentMethodType
from app.domain.enums.payment_provider import PaymentProvider
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.organization import Organization
    from app.domain.models.payment import Payment


class PaymentMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        UniqueConstraint(
            "customer_account_id",
            "provider_payment_method_id",
            name="uq_payment_methods_customer_provider_method",
        ),
        Index("ix_payment_methods_organization_id", "organization_id"),
        Index("ix_payment_methods_customer_account_id", "customer_account_id"),
        Index("ix_payment_methods_is_default", "is_default"),
        Index("ix_payment_methods_is_active", "is_active"),
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

    provider: Mapped[PaymentProvider] = mapped_column(
        SqlEnum(
            PaymentProvider,
            name="payment_provider",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PaymentProvider.MANUAL,
        server_default=PaymentProvider.MANUAL.value,
    )
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_payment_method_id: Mapped[str] = mapped_column(String(255), nullable=False)

    method_type: Mapped[PaymentMethodType] = mapped_column(
        SqlEnum(
            PaymentMethodType,
            name="payment_method_type",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PaymentMethodType.MANUAL,
        server_default=PaymentMethodType.MANUAL.value,
    )
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    exp_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exp_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    organization: Mapped["Organization"] = relationship(lazy="selectin")
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="payment_methods",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="payment_method",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"PaymentMethod(id={self.id!s}, provider={self.provider!r}, "
            f"method_type={self.method_type!r}, is_default={self.is_default!r})"
        )