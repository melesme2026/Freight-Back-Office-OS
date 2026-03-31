from __future__ import annotations

from pathlib import Path
from typing import Any


class OCRService:
    """
    Phase-1 OCR/text extraction service.

    Current behavior:
    - Reads plain text-like files directly when possible
    - Provides safe fallback placeholder output for binary files
    - Keeps the extraction pipeline runnable before full OCR integration

    Future upgrades:
    - PDF text extraction
    - Image OCR
    - DOCX parsing
    - External OCR provider integration
    """

    TEXT_MIME_TYPES = {
        "text/plain",
        "text/csv",
        "application/json",
    }

    TEXT_FILE_EXTENSIONS = {
        ".txt",
        ".csv",
        ".json",
        ".log",
        ".md",
    }

    def extract_text(
        self,
        *,
        storage_key: str,
        original_filename: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        filename = original_filename or Path(storage_key).name
        file_path = Path(storage_key)

        if self._is_direct_text_candidate(file_path=file_path, mime_type=mime_type):
            text = self._read_text_file(file_path)
            if text is not None:
                return {
                    "text": text,
                    "pages": 1,
                    "mime_type": mime_type,
                    "storage_key": storage_key,
                    "extraction_method": "direct_text_read",
                    "ocr_status": "completed",
                }

        return {
            "text": f"OCR placeholder text extracted from {filename}",
            "pages": 1,
            "mime_type": mime_type,
            "storage_key": storage_key,
            "extraction_method": "placeholder",
            "ocr_status": "completed_placeholder",
        }

    def _is_direct_text_candidate(self, *, file_path: Path, mime_type: str | None) -> bool:
        if mime_type and mime_type.lower() in self.TEXT_MIME_TYPES:
            return True

        return file_path.suffix.lower() in self.TEXT_FILE_EXTENSIONS

    def _read_text_file(self, file_path: Path) -> str | None:
        if not file_path.exists() or not file_path.is_file():
            return None

        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = file_path.read_text(encoding=encoding)
                cleaned = text.strip()
                return cleaned or None
            except (OSError, UnicodeDecodeError, ValueError):
                continue

        return None