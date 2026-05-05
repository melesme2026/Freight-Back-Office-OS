from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class DemoRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    company: str = Field(min_length=1, max_length=255)
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

    @field_validator("message", mode="before")
    @classmethod
    def _trim_optional(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class DemoRequestCreateResponse(BaseModel):
    id: str
    status: str
    message: str
