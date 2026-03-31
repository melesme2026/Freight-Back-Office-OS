from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.payment_provider import PaymentProvider
from app.domain.enums.payment_status import PaymentStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class PaymentWebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider: str | None = None
    payload: dict[str, Any] | list[Any] | None = None
    signature: str | None = None


class PaymentWebhookNormalizedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: PaymentProvider
    event_type: str = Field(min_length=1, max_length=100)
    provider_payment_id: str | None = None
    provider_customer_id: str | None = None
    billing_invoice_id: str | None = None
    payment_method_id: str | None = None
    status: PaymentStatus | None = None
    amount: Decimal | None = None
    currency_code: str | None = None
    occurred_at: datetime | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None


class PaymentWebhookAcceptData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed: bool = True
    message: str = "payment webhook received"


class PaymentWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: PaymentWebhookAcceptData
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None