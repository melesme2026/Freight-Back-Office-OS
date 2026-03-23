from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None