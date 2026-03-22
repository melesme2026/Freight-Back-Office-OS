from __future__ import annotations

from typing import Any


class MissingSignatureRule:
    rule_code = "missing_signature"

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        document_type = str(payload.get("document_type", "")).lower()
        extracted_fields = payload.get("extracted_fields", [])

        signature_field = next(
            (item for item in extracted_fields if item.get("field_name") == "signature_present"),
            None,
        )

        if document_type not in {"bill_of_lading", "proof_of_delivery"}:
            return []

        if signature_field is None:
            return [
                {
                    "rule_code": self.rule_code,
                    "severity": "warning",
                    "title": "Signature not detected",
                    "description": "No signature detection field was found for a signed delivery document.",
                    "is_blocking": False,
                }
            ]

        value = str(signature_field.get("field_value_text") or "").strip().lower()
        if value in {"true", "yes", "present", "signed"}:
            return []

        return [
            {
                "rule_code": self.rule_code,
                "severity": "critical",
                "title": "Missing signature",
                "description": "The delivery document appears to be missing a required signature.",
                "is_blocking": True,
            }
        ]