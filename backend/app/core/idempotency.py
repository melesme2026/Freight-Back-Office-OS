from __future__ import annotations

import hashlib
import json
from typing import Any


def build_idempotency_key(
    *,
    scope: str,
    payload: dict[str, Any] | None = None,
    raw_value: str | None = None,
) -> str:
    if raw_value:
        base = f"{scope}:{raw_value}"
    else:
        normalized = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        base = f"{scope}:{normalized}"

    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def build_file_fingerprint(
    *,
    filename: str | None,
    content_type: str | None,
    size_bytes: int | None,
) -> str:
    payload = {
        "filename": filename or "",
        "content_type": content_type or "",
        "size_bytes": size_bytes or 0,
    }
    return build_idempotency_key(scope="file", payload=payload)