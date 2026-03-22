from __future__ import annotations

from decimal import Decimal
from typing import Any


class LLMService:
    def extract_fields(
        self,
        *,
        document_type: str,
        text_content: str,
    ) -> list[dict[str, Any]]:
        normalized_type = (document_type or "").lower()
        text = text_content or ""

        if normalized_type == "rate_confirmation":
            return [
                {
                    "field_name": "document_type",
                    "field_value_text": "rate_confirmation",
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.98"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
                {
                    "field_name": "raw_text_excerpt",
                    "field_value_text": text[:500],
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.80"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
            ]

        if normalized_type == "bill_of_lading":
            return [
                {
                    "field_name": "document_type",
                    "field_value_text": "bill_of_lading",
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.97"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
                {
                    "field_name": "raw_text_excerpt",
                    "field_value_text": text[:500],
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.79"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
            ]

        if normalized_type == "invoice":
            return [
                {
                    "field_name": "document_type",
                    "field_value_text": "invoice",
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.97"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
                {
                    "field_name": "raw_text_excerpt",
                    "field_value_text": text[:500],
                    "field_value_number": None,
                    "field_value_date": None,
                    "field_value_json": None,
                    "confidence_score": Decimal("0.78"),
                    "source_model": "rule-based-llm-placeholder",
                    "source_engine": "local",
                },
            ]

        return [
            {
                "field_name": "document_type",
                "field_value_text": "unknown",
                "field_value_number": None,
                "field_value_date": None,
                "field_value_json": None,
                "confidence_score": Decimal("0.50"),
                "source_model": "rule-based-llm-placeholder",
                "source_engine": "local",
            },
            {
                "field_name": "raw_text_excerpt",
                "field_value_text": text[:500],
                "field_value_number": None,
                "field_value_date": None,
                "field_value_json": None,
                "confidence_score": Decimal("0.55"),
                "source_model": "rule-based-llm-placeholder",
                "source_engine": "local",
            },
        ]