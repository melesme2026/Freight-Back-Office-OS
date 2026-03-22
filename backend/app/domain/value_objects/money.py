from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency_code: str = "USD"

    def __post_init__(self) -> None:
        normalized_amount = self._normalize_amount(self.amount)
        normalized_currency = self.currency_code.upper().strip()

        if not normalized_currency:
            raise ValueError("currency_code cannot be empty")

        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency_code", normalized_currency)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        decimal_value = Decimal(str(value))
        return decimal_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    def add(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency_code=self.currency_code)

    def subtract(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(amount=self.amount - other.amount, currency_code=self.currency_code)

    def multiply(self, factor: Decimal | int | float | str) -> "Money":
        multiplier = Decimal(str(factor))
        return Money(amount=self.amount * multiplier, currency_code=self.currency_code)

    def is_zero(self) -> bool:
        return self.amount == Decimal("0.00")

    def as_dict(self) -> dict[str, str]:
        return {
            "amount": format(self.amount, "f"),
            "currency_code": self.currency_code,
        }

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency_code != other.currency_code:
            raise ValueError(
                f"Currency mismatch: {self.currency_code} != {other.currency_code}"
            )

    def __str__(self) -> str:
        return f"{self.currency_code} {self.amount:.2f}"