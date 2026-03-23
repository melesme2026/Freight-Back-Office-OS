from __future__ import annotations

from typing import Any


class BrokerConsistencyRule:
    rule_code = "broker_consistency"

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        broker_name_raw = str(payload.get("broker_name_raw") or "").strip().lower()
        broker_email_raw = str(payload.get("broker_email_raw") or "").strip().lower()
        extracted_fields = payload.get("extracted_fields", [])

        extracted_broker_name = self._get_text_field(extracted_fields, "broker_name")
        extracted_broker_email = self._get_text_field(extracted_fields, "broker_email")

        issues: list[dict[str, Any]] = []

        if broker_name_raw and extracted_broker_name:
            if broker_name_raw != extracted_broker_name.strip().lower():
                issues.append(
                    {
                        "rule_code": self.rule_code,
                        "severity": "warning",
                        "title": "Broker name mismatch",
                        "description": (
                            "Broker name from load metadata does not match broker name "
                            "detected in extracted document fields."
                        ),
                        "is_blocking": False,
                    }
                )

        if broker_email_raw and extracted_broker_email:
            if broker_email_raw != extracted_broker_email.strip().lower():
                issues.append(
                    {
                        "rule_code": self.rule_code,
                        "severity": "warning",
                        "title": "Broker email mismatch",
                        "description": (
                            "Broker email from load metadata does not match broker email "
                            "detected in extracted document fields."
                        ),
                        "is_blocking": False,
                    }
                )

        return issues

    @staticmethod
    def _get_text_field(
        extracted_fields: list[dict[str, Any]],
        field_name: str,
    ) -> str | None:
        for item in extracted_fields:
            if item.get("field_name") == field_name:
                value = item.get("field_value_text")
                if value:
                    return str(value)
        return None