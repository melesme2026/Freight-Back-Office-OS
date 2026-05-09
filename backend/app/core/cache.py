from __future__ import annotations

import time
from collections.abc import Hashable
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheKey:
    """Tenant-safe cache key with an explicit namespace and organization scope."""

    namespace: str
    organization_id: str | None
    parts: tuple[Hashable, ...] = ()

    def __post_init__(self) -> None:
        namespace = self.namespace.strip()
        if not namespace:
            raise ValueError("cache namespace is required")
        if self.organization_id is not None and not str(self.organization_id).strip():
            raise ValueError("organization_id cannot be blank when provided")
        object.__setattr__(self, "namespace", namespace)
        object.__setattr__(
            self,
            "organization_id",
            str(self.organization_id).strip() if self.organization_id is not None else None,
        )

    def as_tuple(self) -> tuple[Hashable, ...]:
        return (self.namespace, self.organization_id, *self.parts)


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Small in-process TTL cache for safe, bounded operational aggregates.

    This cache is intentionally simple and process-local. It is only for low-risk,
    explicitly scoped calculations that can tolerate short staleness. It must not be
    used for auth/session data, private document payloads, portal tokens, billing
    secrets, webhooks, or globally shared tenant data.
    """

    def __init__(self, *, max_entries: int = 256) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._entries: dict[tuple[Hashable, ...], _CacheEntry[T]] = {}
        self._lock = RLock()

    def get(self, key: CacheKey) -> T | None:
        now = time.monotonic()
        normalized = key.as_tuple()
        with self._lock:
            entry = self._entries.get(normalized)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(normalized, None)
                return None
            return entry.value

    def set(self, key: CacheKey, value: T, *, ttl_seconds: int) -> T:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        now = time.monotonic()
        with self._lock:
            self._prune_expired(now)
            if len(self._entries) >= self.max_entries:
                oldest_key = min(self._entries, key=lambda item: self._entries[item].expires_at)
                self._entries.pop(oldest_key, None)
            self._entries[key.as_tuple()] = _CacheEntry(value=value, expires_at=now + ttl_seconds)
        return value

    def invalidate_namespace(self, namespace: str, *, organization_id: str | None = None) -> int:
        prefix = (
            namespace.strip(),
            str(organization_id).strip() if organization_id is not None else None,
        )
        removed = 0
        with self._lock:
            for key in list(self._entries):
                if key[:2] == prefix:
                    self._entries.pop(key, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune_expired(self, now: float) -> None:
        for key, entry in list(self._entries.items()):
            if entry.expires_at <= now:
                self._entries.pop(key, None)


operational_cache: TTLCache[dict[str, object]] = TTLCache(max_entries=512)
