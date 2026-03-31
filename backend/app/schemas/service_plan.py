from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.billing_cycle import BillingCycle


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ServicePlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None
    billing_cycle: BillingCycle
    base_price: Decimal = Field(ge=Decimal("0"))
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    per_load_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    per_driver_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool = True


class ServicePlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    billing_cycle: BillingCycle | None = None
    base_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    per_load_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    per_driver_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = None


class ServicePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    name: str
    code: str
    description: str | None = None
    billing_cycle: BillingCycle
    base_price: Decimal
    currency_code: str
    per_load_price: Decimal | None = None
    per_driver_price: Decimal | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServicePlanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    name: str
    code: str
    billing_cycle: BillingCycle
    base_price: Decimal
    currency_code: str
    is_active: bool
    created_at: datetime


class ServicePlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ServicePlanRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class ServicePlanListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ServicePlanListItem]
    meta: dict[str, Any]
    error: ApiError | None = None