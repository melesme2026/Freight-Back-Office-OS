from __future__ import annotations

from typing import Any


class MissingRequiredFieldsRule:
    rule_code = "missing_required_fields"

    REQUIRED_FIELDS = [
        "document_type",
        "raw_text_excerpt",
    ]

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        extracted_fields = payload.get("extracted_fields", [])

        present_fields = {
            self._normalize_field_name(item.get("field_name"))
            for item in extracted_fields
            if self._normalize_field_name(item.get("field_name")) is not None
        }

        missing = [
            field_name
            for field_name in self.REQUIRED_FIELDS
            if self._normalize_field_name(field_name) not in present_fields
        ]

        if not missing:
            return []

        return [
            {
                "rule_code": self.rule_code,
                "severity": "error",
                "title": "Missing required fields",
                "description": f"Missing required extracted fields: {', '.join(missing)}",
                "is_blocking": True,
            }
        ]

    @staticmethod
    def _normalize_field_name(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None