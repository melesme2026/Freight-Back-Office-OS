from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.ai.prompt_loader import prompt_loader


class LLMService:
    """
    LLM service with production-safe fallback behavior.

    Current mode:
    - Loads the correct prompt template for the detected document type
    - Keeps the prompt available for future real LLM provider integration
    - Returns deterministic extracted fields using lightweight rule-based parsing
    - Preserves pipeline compatibility with ExtractionService

    Future mode:
    - Replace _run_llm_extraction() internals with actual provider call
      (OpenAI / Azure OpenAI / Anthropic / local model / etc.)
    """

    SOURCE_MODEL = "prompt-aware-rule-based-placeholder"
    SOURCE_ENGINE = "local"

    def extract_fields(
        self,
        *,
        document_type: str,
        text_content: str,
    ) -> list[dict[str, Any]]:
        normalized_type = self._normalize_document_type(document_type)
        text = (text_content or "").strip()

        prompt_template = self._get_prompt_for_document_type(normalized_type)

        _ = self._build_prompt_payload(
            prompt_template=prompt_template,
            text_content=text,
        )

        if normalized_type == "rate_confirmation":
            return self._extract_rate_confirmation_fields(text)

        if normalized_type == "bill_of_lading":
            return self._extract_bol_fields(text)

        if normalized_type == "proof_of_delivery":
            return self._extract_pod_fields(text)

        if normalized_type == "invoice":
            return self._extract_invoice_fields(text)

        return self._extract_unknown_fields(text)

    def _normalize_document_type(self, document_type: str) -> str:
        normalized = (document_type or "").strip().lower()

        if normalized in {"rate_confirmation", "ratecon", "rate_confirm"}:
            return "rate_confirmation"
        if normalized in {"bill_of_lading", "bol", "bill of lading"}:
            return "bill_of_lading"
        if normalized in {
            "proof_of_delivery",
            "proof of delivery",
            "proof-of-delivery",
            "pod",
        }:
            return "proof_of_delivery"
        if normalized in {"invoice"}:
            return "invoice"

        return "unknown"

    def _get_prompt_for_document_type(self, document_type: str) -> str:
        if document_type == "rate_confirmation":
            return prompt_loader.get_ratecon_prompt()
        if document_type == "bill_of_lading":
            return prompt_loader.get_bol_prompt()
        if document_type == "proof_of_delivery":
            return prompt_loader.get_validation_prompt()
        if document_type == "invoice":
            return prompt_loader.get_invoice_prompt()

        return prompt_loader.get_validation_prompt()

    def _build_prompt_payload(
        self,
        *,
        prompt_template: str,
        text_content: str,
    ) -> str:
        return f"{prompt_template}\n\nDOCUMENT_TEXT:\n{text_content}"

    def _extract_rate_confirmation_fields(self, text: str) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = [
            self._text_field("document_type", "rate_confirmation", "0.98"),
            self._text_field("raw_text_excerpt", text[:500] or None, "0.80"),
            self._text_field(
                "load_number",
                self._find_first(
                    text,
                    [
                        r"\bload\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                        r"\bshipment\s*(?:#|number|no\.?)\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.72",
            ),
            self._text_field(
                "rate_confirmation_number",
                self._find_first(
                    text,
                    [
                        r"\brate\s*confirmation\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                        r"\brate\s*con\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.78",
            ),
            self._text_field(
                "broker_name",
                self._find_first(
                    text,
                    [
                        r"\bbroker\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "broker_contact_email",
                self._find_email(text),
                "0.74",
            ),
            self._text_field(
                "pickup_date",
                self._find_first(
                    text,
                    [
                        r"\bpickup\s*date\s*[:\-]?\s*([^\n\r]+)",
                        r"\bship\s*date\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.70",
            ),
            self._text_field(
                "delivery_date",
                self._find_first(
                    text,
                    [
                        r"\bdelivery\s*date\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdeliver\s*by\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.70",
            ),
            self._text_field(
                "pickup_location",
                self._find_first(
                    text,
                    [
                        r"\bpickup\s*(?:location|city|address)?\s*[:\-]?\s*([^\n\r]+)",
                        r"\borigin\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.66",
            ),
            self._text_field(
                "delivery_location",
                self._find_first(
                    text,
                    [
                        r"\bdelivery\s*(?:location|city|address)?\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdestination\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.66",
            ),
            self._number_field(
                "gross_amount",
                self._find_money_decimal(text),
                "0.82",
            ),
        ]

        return self._drop_empty_low_value_fields(fields)

    def _extract_bol_fields(self, text: str) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = [
            self._text_field("document_type", "bill_of_lading", "0.97"),
            self._text_field("raw_text_excerpt", text[:500] or None, "0.79"),
            self._text_field(
                "bol_number",
                self._find_first(
                    text,
                    [
                        r"\bbol\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                        r"\bbill\s+of\s+lading\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.83",
            ),
            self._text_field(
                "load_number",
                self._find_first(
                    text,
                    [
                        r"\bload\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "shipper_name",
                self._find_first(
                    text,
                    [
                        r"\bshipper\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.72",
            ),
            self._text_field(
                "consignee_name",
                self._find_first(
                    text,
                    [
                        r"\bconsignee\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.72",
            ),
            self._text_field(
                "pickup_date",
                self._find_first(
                    text,
                    [
                        r"\bpickup\s*date\s*[:\-]?\s*([^\n\r]+)",
                        r"\bship\s*date\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "delivery_date",
                self._find_first(
                    text,
                    [
                        r"\bdelivery\s*date\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "pickup_location",
                self._find_first(
                    text,
                    [
                        r"\borigin\s*[:\-]?\s*([^\n\r]+)",
                        r"\bpickup\s*(?:location|address|city)?\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.66",
            ),
            self._text_field(
                "delivery_location",
                self._find_first(
                    text,
                    [
                        r"\bdestination\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdelivery\s*(?:location|address|city)?\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.66",
            ),
        ]

        return self._drop_empty_low_value_fields(fields)

    def _extract_pod_fields(self, text: str) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = [
            self._text_field("document_type", "proof_of_delivery", "0.97"),
            self._text_field("raw_text_excerpt", text[:500] or None, "0.79"),
            self._text_field(
                "load_number",
                self._find_first(
                    text,
                    [
                        r"\bload\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.66",
            ),
            self._text_field(
                "bol_number",
                self._find_first(
                    text,
                    [
                        r"\bbol\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                        r"\bbill\s+of\s+lading\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.72",
            ),
            self._text_field(
                "received_by",
                self._find_first(
                    text,
                    [
                        r"\breceived\s+by\s*[:\-]?\s*([^\n\r]+)",
                        r"\breceiver\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.78",
            ),
            self._text_field(
                "delivery_date",
                self._find_first(
                    text,
                    [
                        r"\bdelivery\s*date\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdelivered\s*on\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.74",
            ),
            self._text_field(
                "delivery_location",
                self._find_first(
                    text,
                    [
                        r"\bdestination\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdelivery\s*(?:location|address|city)?\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "signature_present",
                "true" if re.search(r"\bsigned\b|\bsignature\b", text, flags=re.IGNORECASE) else None,
                "0.70",
            ),
        ]

        return self._drop_empty_low_value_fields(fields)

    def _extract_invoice_fields(self, text: str) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = [
            self._text_field("document_type", "invoice", "0.97"),
            self._text_field("raw_text_excerpt", text[:500] or None, "0.78"),
            self._text_field(
                "invoice_number",
                self._find_first(
                    text,
                    [
                        r"\binvoice\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.84",
            ),
            self._text_field(
                "load_number",
                self._find_first(
                    text,
                    [
                        r"\bload\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "bol_number",
                self._find_first(
                    text,
                    [
                        r"\bbol\s*(?:#|number|no\.?)?\s*[:\-]?\s*([A-Z0-9\-]+)\b",
                    ],
                ),
                "0.68",
            ),
            self._text_field(
                "invoice_date",
                self._find_first(
                    text,
                    [
                        r"\binvoice\s*date\s*[:\-]?\s*([^\n\r]+)",
                        r"\bdate\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.72",
            ),
            self._text_field(
                "due_date",
                self._find_first(
                    text,
                    [
                        r"\bdue\s*date\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.74",
            ),
            self._text_field(
                "billing_company_name",
                self._find_first(
                    text,
                    [
                        r"\bbill\s*to\s*[:\-]?\s*([^\n\r]+)",
                        r"\bcustomer\s*[:\-]?\s*([^\n\r]+)",
                    ],
                ),
                "0.70",
            ),
            self._number_field(
                "gross_amount",
                self._find_money_decimal(text),
                "0.84",
            ),
        ]

        return self._drop_empty_low_value_fields(fields)

    def _extract_unknown_fields(self, text: str) -> list[dict[str, Any]]:
        return [
            self._text_field("document_type", "unknown", "0.50"),
            self._text_field("raw_text_excerpt", text[:500] or None, "0.55"),
        ]

    def _text_field(
        self,
        field_name: str,
        field_value_text: str | None,
        confidence_score: str,
    ) -> dict[str, Any]:
        return {
            "field_name": field_name,
            "field_value_text": self._clean_text(field_value_text),
            "field_value_number": None,
            "field_value_date": None,
            "field_value_json": None,
            "confidence_score": Decimal(confidence_score),
            "source_model": self.SOURCE_MODEL,
            "source_engine": self.SOURCE_ENGINE,
        }

    def _number_field(
        self,
        field_name: str,
        field_value_number: Decimal | None,
        confidence_score: str,
    ) -> dict[str, Any]:
        return {
            "field_name": field_name,
            "field_value_text": None,
            "field_value_number": field_value_number,
            "field_value_date": None,
            "field_value_json": None,
            "confidence_score": Decimal(confidence_score),
            "source_model": self.SOURCE_MODEL,
            "source_engine": self.SOURCE_ENGINE,
        }

    def _find_first(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._clean_text(match.group(1))
        return None

    def _find_email(self, text: str) -> str | None:
        match = re.search(
            r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(0)
        return None

    def _find_money_decimal(self, text: str) -> Decimal | None:
        match = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{2})?)", text)
        if not match:
            match = re.search(r"\b([0-9,]+\.[0-9]{2})\b", text)

        if not match:
            return None

        raw_value = match.group(1).replace(",", "")
        try:
            return Decimal(raw_value)
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _clean_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned or None

    def _drop_empty_low_value_fields(self, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for field in fields:
            has_value = (
                field.get("field_value_text") is not None
                or field.get("field_value_number") is not None
                or field.get("field_value_date") is not None
                or field.get("field_value_json") is not None
            )

            if field["field_name"] in {"document_type", "raw_text_excerpt"} or has_value:
                results.append(field)

        return results