from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


class ConfidenceService:
    def average_decimal(self, values: Iterable[Decimal]) -> Decimal | None:
        values_list = [v for v in values if v is not None]

        if not values_list:
            return None

        total = sum(values_list)
        avg = total / Decimal(len(values_list))

        return avg.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)