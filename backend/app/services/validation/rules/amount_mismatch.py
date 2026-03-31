from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class AmountMismatchRule:
    rule_code = "amount_mismatch"

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        extracted_fields = payload.get("extracted_fields", [])

        invoice_amount = self._get_decimal_field(extracted_fields, "invoice_amount")
        ratecon_amount = self._get_decimal_field(extracted_fields, "rate_confirmation_amount")
        gross_amount = payload.get("gross_amount")

        reference_amount = ratecon_amount
        if reference_amount is None and gross_amount is not None:
            try:
                reference_amount = self._normalize_currency_decimal(Decimal(str(gross_amount)))
            except (InvalidOperation, ValueError):
                reference_amount = None

        if invoice_amount is None or reference_amount is None:
            return []

        if invoice_amount == reference_amount:
            return []

        return [
            {
                "rule_code": self.rule_code,
                "severity": "error",
                "title": "Amount mismatch",
                "description": (
                    f"Invoice amount ({invoice_amount}) does not match "
                    f"reference amount ({reference_amount})."
                ),
                "is_blocking": True,
            }
        ]

    @classmethod
    def _get_decimal_field(
        cls,
        extracted_fields: list[dict[str, Any]],
        field_name: str,
    ) -> Decimal | None:
        for item in extracted_fields:
            if item.get("field_name") != field_name:
                continue

            raw_number = item.get("field_value_number")
            raw_text = item.get("field_value_text")

            if raw_number is not None:
                try:
                    return cls._normalize_currency_decimal(Decimal(str(raw_number)))
                except (InvalidOperation, ValueError):
                    return None

            if raw_text:
                try:
                    cleaned = str(raw_text).replace("$", "").replace(",", "").strip()
                    return cls._normalize_currency_decimal(Decimal(cleaned))
                except (InvalidOperation, ValueError):
                    return None

        return None

    @staticmethod
    def _normalize_currency_decimal(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))