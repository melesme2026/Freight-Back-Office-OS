from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    raw: str

    def __post_init__(self) -> None:
        normalized = self._normalize(self.raw)
        if not normalized:
            raise ValueError("Phone number cannot be empty")
        object.__setattr__(self, "raw", normalized)

    @staticmethod
    def _normalize(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""

        has_plus = value.startswith("+")
        digits = re.sub(r"\D", "", value)

        if not digits:
            return ""

        if has_plus:
            return f"+{digits}"

        if len(digits) == 10:
            return f"+1{digits}"

        return f"+{digits}"

    @property
    def e164(self) -> str:
        return self.raw

    @property
    def digits_only(self) -> str:
        return self.raw.lstrip("+")

    @property
    def last4(self) -> str:
        return self.digits_only[-4:]

    def as_dict(self) -> dict[str, str]:
        return {
            "raw": self.raw,
            "e164": self.e164,
            "digits_only": self.digits_only,
            "last4": self.last4,
        }

    def __str__(self) -> str:
        return self.e164