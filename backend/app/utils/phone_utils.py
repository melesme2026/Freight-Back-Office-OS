from __future__ import annotations

import re


def normalize_phone_number(phone: str | None) -> str | None:
    if not phone:
        return None

    digits = re.sub(r"\D+", "", phone)

    if not digits:
        return None

    if len(digits) == 10:
        return f"+1{digits}"

    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    return f"+{digits}"


def last4_phone(phone: str | None) -> str | None:
    normalized = normalize_phone_number(phone)
    if not normalized:
        return None

    digits = re.sub(r"\D+", "", normalized)
    if len(digits) < 4:
        return digits

    return digits[-4:]