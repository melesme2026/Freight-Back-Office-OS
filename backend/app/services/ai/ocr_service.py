from __future__ import annotations

from typing import Any


class OCRService:
    def extract_text(
        self,
        *,
        storage_key: str,
        original_filename: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        filename = original_filename or storage_key.split("/")[-1]

        return {
            "text": f"OCR placeholder text extracted from {filename}",
            "pages": 1,
            "mime_type": mime_type,
            "storage_key": storage_key,
        }