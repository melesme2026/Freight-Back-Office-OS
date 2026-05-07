from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

DEMO_REQUEST_STATUSES = {"new", "contacted", "scheduled", "converted", "closed"}


class DemoRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    company: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    fleet_size: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=5000)

    @field_validator("full_name", "company", mode="before")
    @classmethod
    def _trim_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("phone", "fleet_size", "message", mode="before")
    @classmethod
    def _trim_optional(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class DemoRequestStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1, max_length=50)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in DEMO_REQUEST_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(DEMO_REQUEST_STATUSES))}")
        return normalized


class DemoRequestCreateResponse(BaseModel):
    id: str
    status: str
    message: str
    duplicate: bool = False
