from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class OrganizationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    legal_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    timezone: str = Field(default="America/Toronto", max_length=100)
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True


class OrganizationRead(OrganizationBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    legal_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    timezone: str | None = Field(default=None, max_length=100)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: OrganizationRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None