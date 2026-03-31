from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.onboarding_status import OnboardingStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class OnboardingChecklistBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    documents_received: bool = False
    pricing_confirmed: bool = False
    payment_method_added: bool = False
    driver_profiles_created: bool = False
    channel_connected: bool = False
    go_live_ready: bool = False
    completed_at: datetime | None = None


class OnboardingChecklistUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OnboardingStatus
    documents_received: bool
    pricing_confirmed: bool
    payment_method_added: bool
    driver_profiles_created: bool
    channel_connected: bool
    go_live_ready: bool
    completed_at: datetime | None = None


class OnboardingChecklistRead(OnboardingChecklistBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    created_at: datetime
    updated_at: datetime


class OnboardingChecklistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: OnboardingChecklistRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None