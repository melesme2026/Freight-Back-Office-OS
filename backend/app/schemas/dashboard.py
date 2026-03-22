from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class DashboardSummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loads_total: int
    loads_needing_review: int
    loads_validated: int
    loads_paid: int
    documents_pending_processing: int
    critical_validation_issues: int


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DashboardSummaryData
    meta: dict[str, Any] = {}
    error: ApiError | None = None