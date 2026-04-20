from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.organization import TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.domain.models.broker import Broker
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.extracted_field import ExtractedField
    from app.domain.models.load_document import LoadDocument
    from app.domain.models.notification import Notification
    from app.domain.models.organization import Organization
    from app.domain.models.staff_user import StaffUser
    from app.domain.models.support_ticket import SupportTicket
    from app.domain.models.usage_record import UsageRecord
    from app.domain.models.validation_issue import ValidationIssue
    from app.domain.models.workflow_event import WorkflowEvent


class Load(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loads"
    __table_args__ = (
        Index("ix_loads_organization_id", "organization_id"),
        Index("ix_loads_customer_account_id", "customer_account_id"),
        Index("ix_loads_driver_id", "driver_id"),
        Index("ix_loads_broker_id", "broker_id"),
        Index("ix_loads_status", "status"),
        Index("ix_loads_processing_status", "processing_status"),
        Index("ix_loads_source_channel", "source_channel"),
        Index("ix_loads_load_number", "load_number"),
        Index("ix_loads_rate_confirmation_number", "rate_confirmation_number"),
        Index("ix_loads_bol_number", "bol_number"),
        Index("ix_loads_invoice_number", "invoice_number"),
        Index("ix_loads_pickup_date", "pickup_date"),
        Index("ix_loads_delivery_date", "delivery_date"),
        Index("ix_loads_last_reviewed_by", "last_reviewed_by"),
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
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
    )
    broker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brokers.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_channel: Mapped[Channel] = mapped_column(
        SqlEnum(
            Channel,
            name="channel",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=Channel.MANUAL,
        server_default=Channel.MANUAL.value,
    )
    status: Mapped[LoadStatus] = mapped_column(
        SqlEnum(
            LoadStatus,
            name="load_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LoadStatus.BOOKED,
        server_default=LoadStatus.BOOKED.value,
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SqlEnum(
            ProcessingStatus,
            name="processing_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ProcessingStatus.PENDING,
        server_default=ProcessingStatus.PENDING.value,
    )

    load_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rate_confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bol_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    broker_name_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    broker_email_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)

    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pickup_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    gross_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        server_default="USD",
    )

    documents_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    has_ratecon: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    has_bol: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    has_invoice: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    extraction_confidence_avg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    last_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    follow_up_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    funded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(
        back_populates="loads",
        lazy="selectin",
    )
    customer_account: Mapped["CustomerAccount"] = relationship(
        back_populates="loads",
        lazy="selectin",
    )
    driver: Mapped["Driver"] = relationship(
        back_populates="loads",
        lazy="selectin",
    )
    broker: Mapped["Broker | None"] = relationship(
        back_populates="loads",
        lazy="selectin",
    )
    last_reviewed_by_user: Mapped["StaffUser | None"] = relationship(
        back_populates="reviewed_loads",
        foreign_keys=[last_reviewed_by],
        lazy="selectin",
    )

    documents: Mapped[list["LoadDocument"]] = relationship(
        back_populates="load",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="load",
        lazy="selectin",
    )
    validation_issues: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="load",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="load",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="load",
        lazy="selectin",
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="load",
        lazy="selectin",
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="load",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            "Load("
            f"id={self.id!s}, "
            f"load_number={self.load_number!r}, "
            f"status={self.status!r}, "
            f"processing_status={self.processing_status!r}"
            ")"
        )
