from __future__ import annotations

import hashlib


class FileFingerprintService:
    def build_sha256(self, file_bytes: bytes) -> str:
        if not isinstance(file_bytes, bytes) or not file_bytes:
            raise ValueError("file_bytes must be a non-empty bytes payload")

        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    def build_metadata_fingerprint(
        self,
        *,
        storage_key: str,
        original_filename: str | None = None,
        file_size_bytes: int | None = None,
        mime_type: str | None = None,
    ) -> str:
        normalized_storage_key = (storage_key or "").strip()
        normalized_original_filename = (original_filename or "").strip()
        normalized_mime_type = (mime_type or "").strip().lower()
        normalized_file_size_bytes = str(file_size_bytes or 0)

        raw = "|".join(
            [
                normalized_storage_key,
                normalized_original_filename,
                normalized_file_size_bytes,
                normalized_mime_type,
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()