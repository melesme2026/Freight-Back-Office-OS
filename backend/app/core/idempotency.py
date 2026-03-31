from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.exceptions import ValidationError


def _normalize_scope(scope: str) -> str:
    normalized = scope.strip()
    if not normalized:
        raise ValidationError(
            "Idempotency scope is required",
            details={"field": "scope"},
        )
    return normalized


def _json_default_serializer(value: Any) -> str:
    """
    Deterministic fallback serializer for non-JSON-native values.
    """
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()
    return str(value)


def _normalize_raw_value(raw_value: str | bytes | None) -> str | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="replace")
    normalized = raw_value.strip()
    return normalized or None


def _normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload or {}


def build_idempotency_key(
    *,
    scope: str,
    payload: dict[str, Any] | None = None,
    raw_value: str | bytes | None = None,
) -> str:
    normalized_scope = _normalize_scope(scope)
    normalized_raw_value = _normalize_raw_value(raw_value)

    if normalized_raw_value is not None:
        base = f"{normalized_scope}:{normalized_raw_value}"
    else:
        normalized_payload = _normalize_payload(payload)
        normalized_json = json.dumps(
            normalized_payload,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default_serializer,
            ensure_ascii=False,
        )
        base = f"{normalized_scope}:{normalized_json}"

    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def build_file_fingerprint(
    *,
    filename: str | None,
    content_type: str | None,
    size_bytes: int | None,
) -> str:
    payload = {
        "filename": (filename or "").strip(),
        "content_type": (content_type or "").strip().lower(),
        "size_bytes": int(size_bytes or 0),
    }

    return build_idempotency_key(
        scope="file",
        payload=payload,
    )