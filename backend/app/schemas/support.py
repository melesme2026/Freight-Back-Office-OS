from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class SupportTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: str = Field(default="normal", min_length=1, max_length=50)


class SupportTicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=50)
    priority: str | None = Field(default=None, min_length=1, max_length=50)
    assigned_to_staff_user_id: str | None = None
    resolved_at: datetime | None = None


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    assigned_to_staff_user_id: str | None = None
    subject: str
    description: str
    status: str
    priority: str
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SupportTicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    assigned_to_staff_user_id: str | None = None
    subject: str
    status: str
    priority: str
    resolved_at: datetime | None = None
    created_at: datetime


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: SupportTicketRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class SupportTicketListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[SupportTicketListItem]
    meta: dict[str, Any]
    error: ApiError | None = None