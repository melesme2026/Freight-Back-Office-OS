from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthStatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    environment: str


class ReadinessDependencyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str


class ReadinessStatusData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    database: ReadinessDependencyStatus
    storage: ReadinessDependencyStatus
    redis: ReadinessDependencyStatus
    environment: str


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Any
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: HealthStatusData
    meta: dict[str, Any] = {}
    error: ApiError | None = None


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ReadinessStatusData
    meta: dict[str, Any] = {}
    error: ApiError | None = None