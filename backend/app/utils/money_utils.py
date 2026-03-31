from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


def to_decimal(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def quantize_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_money(value: Decimal | None, currency_code: str = "USD") -> str | None:
    if value is None:
        return None
    amount = quantize_money(value)
    normalized_currency_code = str(currency_code or "USD").strip().upper()
    return f"{normalized_currency_code} {amount}"