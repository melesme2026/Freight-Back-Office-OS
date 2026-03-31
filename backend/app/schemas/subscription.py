from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.subscription_status import SubscriptionStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str
    service_plan_id: str
    starts_at: datetime
    billing_email: EmailStr | None = None
    notes: str | None = None


class SubscriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SubscriptionStatus | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    cancelled_at: datetime | None = None
    billing_email: EmailStr | None = None
    notes: str | None = None


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    service_plan_id: str
    status: SubscriptionStatus
    starts_at: datetime
    ends_at: datetime | None = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None = None
    billing_email: EmailStr | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class SubscriptionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    service_plan_id: str
    status: SubscriptionStatus
    starts_at: datetime
    ends_at: datetime | None = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None = None
    billing_email: EmailStr | None = None
    created_at: datetime


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: SubscriptionRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class SubscriptionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[SubscriptionListItem]
    meta: dict[str, Any]
    error: ApiError | None = None