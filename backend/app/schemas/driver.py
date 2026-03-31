from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class DriverCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    full_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    email: EmailStr | None = None
    is_active: bool = True


class DriverUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    is_active: bool | None = None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str | None = None
    full_name: str
    phone: str
    email: EmailStr | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DriverListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str | None = None
    full_name: str
    phone: str
    email: EmailStr | None = None
    is_active: bool
    created_at: datetime


class DriverResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DriverRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DriverListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[DriverListItem]
    meta: dict[str, Any]
    error: ApiError | None = None