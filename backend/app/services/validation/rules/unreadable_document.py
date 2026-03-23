from __future__ import annotations

from typing import Any


class UnreadableDocumentRule:
    rule_code = "unreadable_document"

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        ocr_text = str(payload.get("ocr_text") or "").strip()
        extracted_fields = payload.get("extracted_fields", [])

        if ocr_text and len(ocr_text) >= 20:
            return []

        if extracted_fields:
            return []

        return [
            {
                "rule_code": self.rule_code,
                "severity": "critical",
                "title": "Unreadable document",
                "description": "The document could not be read reliably by OCR or extraction.",
                "is_blocking": True,
            }
        ]