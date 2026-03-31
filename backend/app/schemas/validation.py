from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.validation_severity import ValidationSeverity


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ValidationIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    load_id: str
    document_id: str | None = None
    rule_code: str
    severity: ValidationSeverity
    title: str
    description: str
    is_blocking: bool
    is_resolved: bool
    resolved_by_staff_user_id: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ValidationIssueResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str | None = Field(default=None, max_length=2000)


class ValidationIssueListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ValidationIssueRead]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class ValidationIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ValidationIssueRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    load_id: str
    driver_name: str | None = None
    load_number: str | None = None
    status: str
    blocking_issue_count: int
    warning_issue_count: int
    extraction_confidence_avg: float | None = None


class ReviewQueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ReviewQueueItem]
    meta: dict[str, Any]
    error: ApiError | None = None