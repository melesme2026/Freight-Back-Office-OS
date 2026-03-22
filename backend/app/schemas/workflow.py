from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.enums.load_status import LoadStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class WorkflowEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    load_id: str
    event_type: str
    old_status: LoadStatus | None = None
    new_status: LoadStatus | None = None
    event_payload: dict[str, Any] | list[Any] | None = None
    actor_staff_user_id: str | None = None
    actor_type: AuditActorType
    created_at: datetime
    updated_at: datetime


class WorkflowStatusTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: LoadStatus
    notes: str | None = Field(default=None, max_length=2000)


class WorkflowStatusTransitionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    old_status: LoadStatus | None = None
    new_status: LoadStatus
    changed_at: datetime


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: WorkflowEventRead
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class WorkflowTimelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[WorkflowEventRead]
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class WorkflowStatusTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: WorkflowStatusTransitionData
    meta: dict[str, Any] = {}
    error: ApiError | None = None