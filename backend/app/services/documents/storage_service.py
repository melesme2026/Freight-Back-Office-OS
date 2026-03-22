from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import NotFoundError


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.storage_local_root_path
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(
        self,
        *,
        relative_path: str,
        content: bytes,
    ) -> str:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return str(destination.relative_to(self.root))

    def read_bytes(
        self,
        *,
        relative_path: str,
    ) -> bytes:
        source = self.root / relative_path
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
        return (self.root / relative_path).exists()

    def delete(
        self,
        *,
        relative_path: str,
    ) -> bool:
        target = self.root / relative_path
        if not target.exists():
            return False
        target.unlink()
        return True

    def absolute_path(
        self,
        *,
        relative_path: str,
    ) -> Path:
        return self.root / relative_path