from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class EmailAttachmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    attachment_id: str | None = None


class EmailWebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider: str | None = None
    payload: dict[str, Any] | list[Any] | None = None


class EmailNormalizedMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    sender_email: EmailStr
    sender_name: str | None = None
    recipient_email: EmailStr | None = None
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    message_id: str | None = None
    received_at: datetime | None = None
    attachments: list[EmailAttachmentPayload] = Field(default_factory=list)
    raw_payload: dict[str, Any] | list[Any] | None = None


class EmailWebhookAcceptData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool = True
    message: str = "email webhook received"


class EmailWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: EmailWebhookAcceptData
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None