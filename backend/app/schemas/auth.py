from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.role import Role


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class StaffUserAuthView(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool = True
    driver_id: str | None = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class LoginResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: StaffUserAuthView


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: LoginResponseData
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: StaffUserAuthView
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None
