from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class AnomalyDetectionService:
    LOW_CONFIDENCE_THRESHOLD = Decimal("0.70")

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def analyze(
        self,
        *,
        extracted_fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        field_names = {
            item.get("field_name")
            for item in extracted_fields
            if item.get("field_name")
        }

        if "document_type" not in field_names:
            issues.append(
                {
                    "code": "missing_document_type",
                    "severity": "warning",
                    "message": "Document type was not identified in extracted fields.",
                }
            )

        confidence_values: list[Decimal] = []
        low_confidence_fields: list[str] = []

        for item in extracted_fields:
            confidence = self._to_decimal(item.get("confidence_score"))
            if confidence is None:
                continue

            confidence_values.append(confidence)

            field_name = item.get("field_name")
            if confidence < self.LOW_CONFIDENCE_THRESHOLD and field_name:
                low_confidence_fields.append(field_name)

        if low_confidence_fields:
            issues.append(
                {
                    "code": "low_confidence_fields",
                    "severity": "warning",
                    "message": "Some extracted fields have low confidence.",
                    "fields": low_confidence_fields,
                }
            )

        average_confidence = None
        if confidence_values:
            average_confidence = sum(confidence_values) / Decimal(len(confidence_values))

        return {
            "is_anomalous": len(issues) > 0,
            "issue_count": len(issues),
            "average_confidence": average_confidence,
            "issues": issues,
        }