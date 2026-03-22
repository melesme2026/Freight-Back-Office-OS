from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ReferralCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    referred_by_name: str = Field(min_length=1, max_length=255)
    referred_by_phone: str | None = Field(default=None, max_length=50)
    referred_by_email: EmailStr | None = None
    notes: str | None = None


class ReferralRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str | None = None
    referred_by_name: str
    referred_by_phone: str | None = None
    referred_by_email: EmailStr | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ReferralListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str | None = None
    referred_by_name: str
    referred_by_phone: str | None = None
    referred_by_email: EmailStr | None = None
    created_at: datetime


class ReferralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ReferralRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class ReferralListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ReferralListItem]
    meta: dict[str, Any]
    error: ApiError | None = None