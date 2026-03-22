from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.invoice_status import InvoiceStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class BillingInvoiceLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    quantity: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0"))
    unit_price: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0"))
    usage_record_id: str | None = None
    metadata_json: dict[str, Any] | list[Any] | None = None


class BillingInvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    invoice_id: str
    usage_record_id: str | None = None
    line_type: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    metadata_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime


class BillingInvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str
    subscription_id: str | None = None
    issued_at: datetime
    due_at: datetime | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    currency_code: str = Field(default="USD", min_length=3, max_length=3)
    lines: list[BillingInvoiceLineCreate] = Field(default_factory=list)
    notes: str | None = None


class BillingInvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InvoiceStatus | None = None
    issued_at: datetime | None = None
    due_at: datetime | None = None
    paid_at: datetime | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    notes: str | None = None


class BillingInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    subscription_id: str | None = None
    invoice_number: str
    status: InvoiceStatus
    currency_code: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    issued_at: datetime
    due_at: datetime | None = None
    paid_at: datetime | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[BillingInvoiceLineRead] = Field(default_factory=list)


class BillingInvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    subscription_id: str | None = None
    invoice_number: str
    status: InvoiceStatus
    currency_code: str
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    issued_at: datetime
    due_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime


class BillingInvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: BillingInvoiceRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class BillingInvoiceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[BillingInvoiceListItem]
    meta: dict[str, Any]
    error: ApiError | None = None