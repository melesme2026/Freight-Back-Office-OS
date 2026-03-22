from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.payment_method_type import PaymentMethodType
from app.domain.enums.payment_provider import PaymentProvider
from app.domain.enums.payment_status import PaymentStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class PaymentMethodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str
    provider: PaymentProvider
    provider_customer_id: str | None = Field(default=None, max_length=255)
    provider_payment_method_id: str = Field(min_length=1, max_length=255)
    method_type: PaymentMethodType
    brand: str | None = Field(default=None, max_length=50)
    last4: str | None = Field(default=None, min_length=4, max_length=4)
    exp_month: int | None = Field(default=None, ge=1, le=12)
    exp_year: int | None = Field(default=None, ge=2000, le=9999)
    is_default: bool = False
    is_active: bool = True


class PaymentMethodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_customer_id: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=50)
    last4: str | None = Field(default=None, min_length=4, max_length=4)
    exp_month: int | None = Field(default=None, ge=1, le=12)
    exp_year: int | None = Field(default=None, ge=2000, le=9999)
    is_default: bool | None = None
    is_active: bool | None = None


class PaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    provider: PaymentProvider
    provider_customer_id: str | None = None
    provider_payment_method_id: str
    method_type: PaymentMethodType
    brand: str | None = None
    last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaymentMethodListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    provider: PaymentProvider
    method_type: PaymentMethodType
    brand: str | None = None
    last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    is_default: bool
    is_active: bool
    created_at: datetime


class PaymentCollectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    billing_invoice_id: str
    payment_method_id: str | None = None
    amount: Decimal = Field(ge=Decimal("0.01"))


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    billing_invoice_id: str | None = None
    payment_method_id: str | None = None
    driver_id: str | None = None
    recorded_by_staff_user_id: str | None = None
    provider: PaymentProvider
    provider_payment_id: str | None = None
    status: PaymentStatus
    amount: Decimal
    currency_code: str
    attempted_at: datetime | None = None
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    metadata_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime


class PaymentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    billing_invoice_id: str | None = None
    payment_method_id: str | None = None
    provider: PaymentProvider
    status: PaymentStatus
    amount: Decimal
    currency_code: str
    attempted_at: datetime | None = None
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime


class PaymentMethodResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: PaymentMethodRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class PaymentMethodListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[PaymentMethodListItem]
    meta: dict[str, Any]
    error: ApiError | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: PaymentRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class PaymentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[PaymentListItem]
    meta: dict[str, Any]
    error: ApiError | None = None