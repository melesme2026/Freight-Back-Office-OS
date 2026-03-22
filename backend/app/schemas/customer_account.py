from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.customer_account_status import CustomerAccountStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class CustomerAccountBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str = Field(min_length=1, max_length=255)
    account_code: str | None = Field(default=None, max_length=50)
    status: CustomerAccountStatus = CustomerAccountStatus.PROSPECT
    primary_contact_name: str | None = Field(default=None, max_length=255)
    primary_contact_email: EmailStr | None = None
    primary_contact_phone: str | None = Field(default=None, max_length=50)
    billing_email: EmailStr | None = None
    notes: str | None = None


class CustomerAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str = Field(min_length=1, max_length=255)
    account_code: str | None = Field(default=None, max_length=50)
    primary_contact_name: str | None = Field(default=None, max_length=255)
    primary_contact_email: EmailStr | None = None
    primary_contact_phone: str | None = Field(default=None, max_length=50)
    billing_email: EmailStr | None = None
    notes: str | None = None


class CustomerAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str | None = Field(default=None, min_length=1, max_length=255)
    account_code: str | None = Field(default=None, max_length=50)
    status: CustomerAccountStatus | None = None
    primary_contact_name: str | None = Field(default=None, max_length=255)
    primary_contact_email: EmailStr | None = None
    primary_contact_phone: str | None = Field(default=None, max_length=50)
    billing_email: EmailStr | None = None
    notes: str | None = None


class CustomerAccountRead(CustomerAccountBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class CustomerAccountListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    account_name: str
    account_code: str | None = None
    status: CustomerAccountStatus
    primary_contact_name: str | None = None
    billing_email: EmailStr | None = None
    created_at: datetime


class CustomerAccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: CustomerAccountRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class CustomerAccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[CustomerAccountListItem]
    meta: dict[str, Any]
    error: ApiError | None = None