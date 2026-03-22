from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class BrokerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    mc_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    notes: str | None = None


class BrokerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    mc_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    notes: str | None = None


class BrokerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    name: str
    mc_number: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    payment_terms_days: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class BrokerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    name: str
    mc_number: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    payment_terms_days: int | None = None
    created_at: datetime


class BrokerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: BrokerRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class BrokerListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[BrokerListItem]
    meta: dict[str, Any]
    error: ApiError | None = None