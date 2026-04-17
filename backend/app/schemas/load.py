from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class LoadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str
    driver_id: str
    broker_id: str | None = None
    source_channel: Channel = Channel.MANUAL
    load_number: str | None = Field(default=None, max_length=100)
    rate_confirmation_number: str | None = Field(default=None, max_length=100)
    bol_number: str | None = Field(default=None, max_length=100)
    invoice_number: str | None = Field(default=None, max_length=100)
    broker_name_raw: str | None = Field(default=None, max_length=255)
    broker_email_raw: str | None = Field(default=None, max_length=255)
    pickup_date: date | None = None
    delivery_date: date | None = None
    pickup_location: str | None = Field(default=None, max_length=255)
    delivery_location: str | None = Field(default=None, max_length=255)
    gross_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    notes: str | None = None


class LoadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    driver_id: str | None = None
    broker_id: str | None = None
    source_channel: Channel | None = None
    load_number: str | None = Field(default=None, max_length=100)
    rate_confirmation_number: str | None = Field(default=None, max_length=100)
    bol_number: str | None = Field(default=None, max_length=100)
    invoice_number: str | None = Field(default=None, max_length=100)
    broker_name_raw: str | None = Field(default=None, max_length=255)
    broker_email_raw: str | None = Field(default=None, max_length=255)
    pickup_date: date | None = None
    delivery_date: date | None = None
    pickup_location: str | None = Field(default=None, max_length=255)
    delivery_location: str | None = Field(default=None, max_length=255)
    gross_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    documents_complete: bool | None = None
    has_ratecon: bool | None = None
    has_bol: bool | None = None
    has_invoice: bool | None = None
    follow_up_required: bool | None = None
    notes: str | None = None


class LoadStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: LoadStatus
    notes: str | None = None


class LoadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    driver_id: str
    broker_id: str | None = None
    source_channel: Channel
    status: LoadStatus
    processing_status: ProcessingStatus
    load_number: str | None = None
    rate_confirmation_number: str | None = None
    bol_number: str | None = None
    invoice_number: str | None = None
    broker_name_raw: str | None = None
    broker_email_raw: str | None = None
    pickup_date: date | None = None
    delivery_date: date | None = None
    pickup_location: str | None = None
    delivery_location: str | None = None
    gross_amount: Decimal | None = None
    currency_code: str
    documents_complete: bool
    has_ratecon: bool
    has_bol: bool
    has_invoice: bool
    extraction_confidence_avg: Decimal | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    last_contacted_at: datetime | None = None
    follow_up_required: bool = False
    submitted_at: datetime | None = None
    funded_at: datetime | None = None
    paid_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LoadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    driver_id: str
    broker_id: str | None = None
    source_channel: Channel
    status: LoadStatus
    processing_status: ProcessingStatus
    load_number: str | None = None
    rate_confirmation_number: str | None = None
    bol_number: str | None = None
    gross_amount: Decimal | None = None
    currency_code: str
    pickup_date: date | None = None
    delivery_date: date | None = None
    documents_complete: bool
    created_at: datetime
    updated_at: datetime


class WorkflowEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    load_id: str
    event_type: str
    old_status: str | None = None
    new_status: str | None = None
    actor_staff_user_id: str | None = None
    actor_type: str
    created_at: datetime


class LoadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: LoadRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class LoadListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[LoadListItem]
    meta: dict[str, Any]
    error: ApiError | None = None


class LoadTimelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[WorkflowEventRead]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class LoadStatusUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None
