from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class WhatsAppWebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    object: str | None = None
    entry: list[dict[str, Any]] = Field(default_factory=list)


class WhatsAppNormalizedMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    sender_phone: str
    sender_name: str | None = None
    message_id: str | None = None
    message_type: str
    text_body: str | None = None
    media_id: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    timestamp: datetime | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None


class WhatsAppWebhookAcceptData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool = True
    message: str = "whatsapp webhook received"


class WhatsAppWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: WhatsAppWebhookAcceptData
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None