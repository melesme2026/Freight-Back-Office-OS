from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    value: float

    def __post_init__(self) -> None:
        normalized = float(self.value)
        if normalized < 0.0 or normalized > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        object.__setattr__(self, "value", normalized)

    @property
    def percentage(self) -> float:
        return round(self.value * 100, 2)

    @property
    def is_high(self) -> bool:
        return self.value >= 0.9

    @property
    def is_medium(self) -> bool:
        return 0.7 <= self.value < 0.9

    @property
    def is_low(self) -> bool:
        return self.value < 0.7

    def as_dict(self) -> dict[str, float]:
        return {
            "value": round(self.value, 4),
            "percentage": self.percentage,
        }

    def __str__(self) -> str:
        return f"{self.percentage:.2f}%"