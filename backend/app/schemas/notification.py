from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.channel import Channel
from app.domain.enums.notification_status import NotificationStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class NotificationSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    channel: Channel
    message_type: str = Field(min_length=1, max_length=100)
    subject: str | None = Field(default=None, max_length=255)
    body_text: str | None = None
    direction: str = Field(default="outbound", min_length=1, max_length=20)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    created_by_staff_user_id: str | None = None
    channel: Channel
    direction: str
    message_type: str
    subject: str | None = None
    body_text: str | None = None
    provider_message_id: str | None = None
    status: NotificationStatus
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    channel: Channel
    direction: str
    message_type: str
    status: NotificationStatus
    customer_account_id: str | None = None
    driver_id: str | None = None
    load_id: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: NotificationRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[NotificationListItem]
    meta: dict[str, Any]
    error: ApiError | None = None