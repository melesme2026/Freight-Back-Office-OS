from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.storage_local_root_path.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile) -> dict[str, str | int | None]:
        safe_original_filename = self._normalize_upload_filename(file.filename)
        resolved_mime_type = self._normalize_optional_text(file.content_type) or self._guess_mime_type(
            safe_original_filename
        )

        suffix = Path(safe_original_filename).suffix
        generated_filename = f"{uuid.uuid4().hex}{suffix}"

        top_level_folder = self._folder_for_content_type(resolved_mime_type)
        relative_path = f"{top_level_folder}/{generated_filename}"

        content = await file.read()
        if content is None:
            content = b""

        stored_relative_path = self.save_bytes(
            relative_path=relative_path,
            content=content,
            overwrite=False,
        )

        return {
            "storage_key": stored_relative_path,
            "bucket": None,
            "size": len(content),
            "original_filename": safe_original_filename,
            "mime_type": resolved_mime_type,
        }

    def get_file(
        self,
        relative_path: str,
        *,
        download_filename: str | None = None,
        media_type: str | None = None,
    ) -> FileResponse:
        return self.get_file_response(
            relative_path=relative_path,
            download_filename=download_filename,
            media_type=media_type,
        )

    def get_file_response(
        self,
        *,
        relative_path: str,
        download_filename: str | None = None,
        media_type: str | None = None,
    ) -> FileResponse:
        absolute_path = self.absolute_path(relative_path=relative_path)

        if not absolute_path.exists() or not absolute_path.is_file():
            raise NotFoundError(
                "Stored file not found",
                details={"relative_path": relative_path},
            )

        resolved_filename = self._normalize_optional_text(download_filename) or absolute_path.name
        resolved_media_type = media_type or self._guess_mime_type(resolved_filename)

        return FileResponse(
            path=absolute_path,
            filename=resolved_filename,
            media_type=resolved_media_type,
        )

    def save_bytes(
        self,
        *,
        relative_path: str,
        content: bytes,
        overwrite: bool = False,
    ) -> str:
        destination = self._resolve_relative_path(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists() and not overwrite:
            raise ValidationError(
                "A file already exists at the requested storage path",
                details={"relative_path": relative_path},
            )

        destination.write_bytes(content)
        return str(destination.relative_to(self.root)).replace("\\", "/")

    def read_bytes(
        self,
        *,
        relative_path: str,
    ) -> bytes:
        source = self._resolve_relative_path(relative_path)
        if not source.exists() or not source.is_file():
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
        candidate = self._resolve_relative_path(relative_path)
        return candidate.exists() and candidate.is_file()

    def delete(
        self,
        *,
        relative_path: str,
    ) -> bool:
        target = self._resolve_relative_path(relative_path)
        if not target.exists() or not target.is_file():
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
        cleaned_relative_path = self._normalize_required_text("relative_path", relative_path)
        candidate = (self.root / cleaned_relative_path).resolve()

        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValidationError(
                "relative_path must stay within storage root",
                details={"relative_path": relative_path},
            ) from exc

        return candidate

    def _normalize_upload_filename(self, filename: str | None) -> str:
        normalized_filename = self._normalize_optional_text(filename)
        if normalized_filename is None:
            raise ValidationError(
                "Uploaded file must have a filename",
                details={"filename": filename},
            )

        safe_original_filename = Path(normalized_filename).name.strip()
        if not safe_original_filename:
            raise ValidationError(
                "Uploaded file must have a valid filename",
                details={"filename": filename},
            )

        return safe_original_filename

    def _folder_for_content_type(self, content_type: str | None) -> str:
        normalized = (content_type or "").strip().lower()

        if normalized.startswith("image/"):
            return "images"
        if normalized == "application/pdf":
            return "pdfs"
        if normalized.startswith("text/"):
            return "text"
        return "uploads"

    def _guess_mime_type(self, filename: str) -> str:
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @classmethod
    def _normalize_required_text(cls, field_name: str, value: str | None) -> str:
        normalized = cls._normalize_optional_text(value)
        if normalized is None:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return normalized