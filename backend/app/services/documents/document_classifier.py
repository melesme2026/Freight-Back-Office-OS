from __future__ import annotations

import re
from typing import Any

from app.domain.enums.document_type import DocumentType


class DocumentClassifier:
    def classify(
        self,
        *,
        original_filename: str | None = None,
        mime_type: str | None = None,
        text_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[DocumentType, float]:
        filename = (original_filename or "").lower()
        mime = (mime_type or "").lower()
        text = (text_content or "").lower()
        extra = str(metadata or {}).lower()

        combined = " ".join([filename, mime, text, extra])
        normalized = self._normalize_text(combined)

        scores: dict[DocumentType, float] = {
            DocumentType.RATE_CONFIRMATION: 0.0,
            DocumentType.BILL_OF_LADING: 0.0,
            DocumentType.PROOF_OF_DELIVERY: 0.0,
            DocumentType.INVOICE: 0.0,
            DocumentType.UNKNOWN: 0.0,
        }

        # Rate Confirmation
        scores[DocumentType.RATE_CONFIRMATION] += self._score_matches(
            normalized,
            {
                r"\brate confirmation\b": 0.65,
                r"\bratecon\b": 0.55,
                r"\brate cons?\b": 0.45,
                r"\brate-confirmation\b": 0.55,
                r"\bbroker\b": 0.10,
                r"\bcarrier\b": 0.10,
                r"\bdispatch\b": 0.08,
                r"\bgross amount\b": 0.10,
            },
        )

        # Bill of Lading
        scores[DocumentType.BILL_OF_LADING] += self._score_matches(
            normalized,
            {
                r"\bbill of lading\b": 0.70,
                r"\bb\.?\s*o\.?\s*l\.?\b": 0.55,
                r"\bshipper\b": 0.12,
                r"\bconsignee\b": 0.12,
                r"\bcommodity\b": 0.10,
                r"\bpieces\b": 0.08,
            },
        )

        # Proof of Delivery
        scores[DocumentType.PROOF_OF_DELIVERY] += self._score_matches(
            normalized,
            {
                r"\bproof of delivery\b": 0.75,
                r"\bpod\b": 0.35,
                r"\bdelivered\b": 0.12,
                r"\breceived by\b": 0.12,
                r"\bsigned\b": 0.10,
            },
        )

        # Invoice
        scores[DocumentType.INVOICE] += self._score_matches(
            normalized,
            {
                r"\binvoice\b": 0.60,
                r"\binvoice number\b": 0.20,
                r"\binv #\b": 0.18,
                r"\bbill to\b": 0.12,
                r"\bdue date\b": 0.12,
                r"\bpayment terms\b": 0.10,
                r"\bremit to\b": 0.12,
            },
        )

        # File-name hints
        scores[DocumentType.RATE_CONFIRMATION] += self._filename_hint_score(
            filename,
            ["ratecon", "rate_confirmation", "rate-confirmation", "rate conf"],
            0.20,
        )
        scores[DocumentType.BILL_OF_LADING] += self._filename_hint_score(
            filename,
            ["bol", "bill_of_lading", "bill-of-lading"],
            0.20,
        )
        scores[DocumentType.PROOF_OF_DELIVERY] += self._filename_hint_score(
            filename,
            ["pod", "proof_of_delivery", "proof-of-delivery", "signed_delivery"],
            0.20,
        )
        scores[DocumentType.INVOICE] += self._filename_hint_score(
            filename,
            ["invoice", "inv_", "inv-", "billing"],
            0.20,
        )

        # Image + signed hint for POD
        if filename.endswith((".jpg", ".jpeg", ".png", ".webp")) and "signed" in normalized:
            scores[DocumentType.PROOF_OF_DELIVERY] += 0.18

        best_type = max(
            (
                DocumentType.RATE_CONFIRMATION,
                DocumentType.BILL_OF_LADING,
                DocumentType.PROOF_OF_DELIVERY,
                DocumentType.INVOICE,
            ),
            key=lambda doc_type: scores[doc_type],
        )

        best_score = min(scores[best_type], 0.99)

        if best_score < 0.45:
            return DocumentType.UNKNOWN, 0.40

        return best_type, round(best_score, 2)

    def _score_matches(self, text: str, weighted_patterns: dict[str, float]) -> float:
        total = 0.0
        for pattern, weight in weighted_patterns.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                total += weight
        return total

    def _filename_hint_score(self, filename: str, hints: list[str], score: float) -> float:
        lowered = filename.lower()
        return score if any(hint in lowered for hint in hints) else 0.0

    def _normalize_text(self, value: str) -> str:
        value = value.lower()
        value = re.sub(r"[_\-]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value