from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    id: str
    job_type: str
    organization_id: str | None
    entity_type: str | None
    entity_id: str | None
    idempotency_key: str | None
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_error: str | None = None
    result: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "organization_id": self.organization_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_error": self.last_error,
            "result": self.result,
        }


class InProcessJobQueue:
    """Low-risk background job foundation for FastAPI BackgroundTasks.

    The queue records retry bounds, idempotency keys, org/entity context, failures,
    and status in memory. It is deliberately not a distributed worker replacement;
    it gives upload/export paths a safe async hook now and a clean seam for Redis/RQ
    or Celery later.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._idempotency_index: dict[str, str] = {}
        self._lock = RLock()

    def enqueue(
        self,
        *,
        job_type: str,
        organization_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> JobRecord:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        normalized_idempotency_key = idempotency_key.strip() if idempotency_key else None
        with self._lock:
            if normalized_idempotency_key and normalized_idempotency_key in self._idempotency_index:
                return self._jobs[self._idempotency_index[normalized_idempotency_key]]
            record = JobRecord(
                id=str(uuid.uuid4()),
                job_type=job_type.strip(),
                organization_id=str(organization_id).strip() if organization_id else None,
                entity_type=entity_type.strip() if entity_type else None,
                entity_id=str(entity_id).strip() if entity_id else None,
                idempotency_key=normalized_idempotency_key,
                max_attempts=max_attempts,
            )
            self._jobs[record.id] = record
            if normalized_idempotency_key:
                self._idempotency_index[normalized_idempotency_key] = record.id
            return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def run(self, job_id: str, func: Callable[[], dict[str, Any] | None]) -> JobRecord | None:
        record = self.get(job_id)
        if record is None:
            logger.warning("Background job was not found", extra={"job_id": job_id})
            return None
        with self._lock:
            if record.status == JobStatus.COMPLETED:
                return record
            if record.attempts >= record.max_attempts:
                record.status = JobStatus.FAILED
                record.updated_at = datetime.now(timezone.utc)
                return record
            record.status = JobStatus.PROCESSING
            record.attempts += 1
            record.updated_at = datetime.now(timezone.utc)
        try:
            result = func() or {}
        except Exception as exc:  # job failure must not affect original request
            logger.exception(
                "Background job failed",
                extra={
                    "job_id": record.id,
                    "job_type": record.job_type,
                    "organization_id": record.organization_id,
                    "entity_type": record.entity_type,
                    "entity_id": record.entity_id,
                    "attempts": record.attempts,
                },
            )
            with self._lock:
                record.last_error = str(exc)
                record.status = (
                    JobStatus.FAILED if record.attempts >= record.max_attempts else JobStatus.QUEUED
                )
                record.updated_at = datetime.now(timezone.utc)
            return record
        with self._lock:
            record.status = JobStatus.COMPLETED
            record.result = result
            record.last_error = None
            record.updated_at = datetime.now(timezone.utc)
        return record

    def reset(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._idempotency_index.clear()


job_queue = InProcessJobQueue()
