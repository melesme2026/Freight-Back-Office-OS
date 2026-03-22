from __future__ import annotations

import hashlib


class FileFingerprintService:
    def build_sha256(self, file_bytes: bytes) -> str:
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
        raw = "|".join(
            [
                storage_key or "",
                original_filename or "",
                str(file_size_bytes or 0),
                mime_type or "",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()