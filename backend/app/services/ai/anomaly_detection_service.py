from __future__ import annotations

from decimal import Decimal
from typing import Any


class AnomalyDetectionService:
    def analyze(
        self,
        *,
        extracted_fields: list[dict[str, Any]],
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        field_names = {item.get("field_name") for item in extracted_fields}

        if "document_type" not in field_names:
            issues.append(
                {
                    "code": "missing_document_type",
                    "severity": "warning",
                    "message": "Document type was not identified in extracted fields.",
                }
            )

        confidence_values: list[Decimal] = []
        for item in extracted_fields:
            raw_confidence = item.get("confidence_score")
            if raw_confidence is None:
                continue
            confidence_values.append(Decimal(str(raw_confidence)))

        low_confidence_fields = [
            item.get("field_name")
            for item in extracted_fields
            if item.get("confidence_score") is not None
            and Decimal(str(item["confidence_score"])) < Decimal("0.70")
        ]

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