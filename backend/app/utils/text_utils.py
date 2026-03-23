from __future__ import annotations

import re


def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    normalized = normalize_whitespace(value) or ""
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def contains_any(text: str | None, patterns: list[str]) -> bool:
    haystack = (text or "").lower()
    return any(pattern.lower() in haystack for pattern in patterns)