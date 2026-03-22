from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.enums.payment_status import PaymentStatus
from app.domain.enums.subscription_status import SubscriptionStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class BillingSummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mrr_estimate: Decimal
    open_invoices_count: int
    past_due_invoices_count: int
    payments_collected_this_month: Decimal
    active_subscriptions_count: int


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


class PaymentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    billing_invoice_id: str | None = None
    payment_method_id: str | None = None
    status: PaymentStatus
    provider: str
    amount: Decimal
    currency_code: str
    attempted_at: datetime | None = None
    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime


class SubscriptionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    customer_account_id: str
    service_plan_id: str
    status: SubscriptionStatus
    starts_at: datetime
    ends_at: datetime | None = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None = None


class BillingDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: BillingSummaryData
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class BillingInvoiceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[BillingInvoiceListItem]
    meta: dict[str, Any]
    error: ApiError | None = None


class PaymentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[PaymentListItem]
    meta: dict[str, Any]
    error: ApiError | None = None


class SubscriptionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[SubscriptionListItem]
    meta: dict[str, Any]
    error: ApiError | None = None


class BillingPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None