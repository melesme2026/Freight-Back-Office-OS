from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.storage_local_root_path.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(
        self,
        *,
        relative_path: str,
        content: bytes,
    ) -> str:
        destination = self._resolve_relative_path(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return str(destination.relative_to(self.root))

    def read_bytes(
        self,
        *,
        relative_path: str,
    ) -> bytes:
        source = self._resolve_relative_path(relative_path)
        if not source.exists():
            raise NotFoundError(
                "Stored file not found",
                details={"relative_path": relative_path},
            )
        return source.read_bytes()

    def exists(
        self,
        *,
        relative_path: str,
    ) -> bool:
        return self._resolve_relative_path(relative_path).exists()

    def delete(
        self,
        *,
        relative_path: str,
    ) -> bool:
        target = self._resolve_relative_path(relative_path)
        if not target.exists():
            return False
        target.unlink()
        return True

    def absolute_path(
        self,
        *,
        relative_path: str,
    ) -> Path:
        return self._resolve_relative_path(relative_path)

    def _resolve_relative_path(self, relative_path: str) -> Path:
        cleaned_relative_path = str(relative_path).strip()

        if not cleaned_relative_path:
            raise ValidationError(
                "relative_path is required",
                details={"relative_path": relative_path},
            )

        candidate = (self.root / cleaned_relative_path).resolve()

        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValidationError(
                "relative_path must stay within storage root",
                details={"relative_path": relative_path},
            ) from exc

        return candidate