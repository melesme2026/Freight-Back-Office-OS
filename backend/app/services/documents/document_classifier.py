from __future__ import annotations

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
        extra = metadata or {}

        combined = " ".join(
            [
                filename,
                mime,
                text,
                str(extra).lower(),
            ]
        )

        if self._contains_any(
            combined,
            [
                "rate confirmation",
                "ratecon",
                "rate cons",
                "rate-confirmation",
                "rate sheet",
            ],
        ):
            return DocumentType.RATE_CONFIRMATION, 0.95

        if self._contains_any(
            combined,
            [
                "bill of lading",
                "bol",
                "b.o.l",
                "proof of delivery",
                "pod signed",
            ],
        ):
            if "proof of delivery" in combined or "pod" in combined:
                return DocumentType.PROOF_OF_DELIVERY, 0.91
            return DocumentType.BILL_OF_LADING, 0.94

        if self._contains_any(
            combined,
            [
                "invoice",
                "inv #",
                "invoice number",
                "billing statement",
            ],
        ):
            return DocumentType.INVOICE, 0.93

        if filename.endswith((".jpg", ".jpeg", ".png", ".webp")) and "signed" in combined:
            return DocumentType.PROOF_OF_DELIVERY, 0.72

        return DocumentType.UNKNOWN, 0.40

    @staticmethod
    def _contains_any(text: str, candidates: list[str]) -> bool:
        return any(candidate in text for candidate in candidates)