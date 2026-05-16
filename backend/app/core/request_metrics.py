from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass


@dataclass
class RequestMetrics:
    query_count: int = 0
    db_query_time_ms: float = 0.0


_request_metrics: contextvars.ContextVar[RequestMetrics | None] = (
    contextvars.ContextVar("request_metrics", default=None)
)
_query_started_at: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "query_started_at", default=None
)


def start_request_metrics() -> contextvars.Token[RequestMetrics | None]:
    return _request_metrics.set(RequestMetrics())


def reset_request_metrics(token: contextvars.Token[RequestMetrics | None]) -> None:
    _request_metrics.reset(token)


def get_request_metrics() -> RequestMetrics | None:
    return _request_metrics.get()


def mark_query_start() -> contextvars.Token[float | None]:
    return _query_started_at.set(time.perf_counter())


def mark_query_end(token: contextvars.Token[float | None]) -> None:
    started_at = _query_started_at.get()
    metrics = _request_metrics.get()
    if metrics is not None:
        metrics.query_count += 1
        if isinstance(started_at, (int, float)):
            metrics.db_query_time_ms += (time.perf_counter() - started_at) * 1000
    _query_started_at.reset(token)
