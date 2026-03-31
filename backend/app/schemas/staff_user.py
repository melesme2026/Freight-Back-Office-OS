from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.role import Role


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class StaffUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    role: Role = Role.OPS_AGENT


class StaffUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=255)
    role: Role | None = None
    is_active: bool | None = None


class StaffUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StaffUserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class StaffUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: StaffUserRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class StaffUserListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[StaffUserListItem]
    meta: dict[str, Any]
    error: ApiError | None = None