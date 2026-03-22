from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DateRange:
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def contains(self, value: date) -> bool:
        return self.start_date <= value <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        return not (self.end_date < other.start_date or other.end_date < self.start_date)

    def as_dict(self) -> dict[str, str | int]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days": self.days,
        }

    def __str__(self) -> str:
        return f"{self.start_date.isoformat()} -> {self.end_date.isoformat()}"