from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.load_document import LoadDocument
from app.services.documents.storage_service import StorageService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanupCandidate:
    relative_path: str
    reason: str
    size_bytes: int
    last_modified_at: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "reason": self.reason,
            "size_bytes": self.size_bytes,
            "last_modified_at": self.last_modified_at,
        }


class StorageCleanupService:
    DEFAULT_RETENTION_DAYS = 30
    TEMP_RETENTION_DAYS = 2
    MAX_SCAN_FILES = 5000
    TEMP_PREFIXES = ("tmp/", "temp/", "exports/tmp/")
    MANAGED_PREFIXES = ("pdfs/", "images/", "uploads/", "text/", "tmp/", "temp/", "exports/")

    def __init__(self, db: Session, storage: StorageService | None = None) -> None:
        self.db = db
        self.storage = storage or StorageService()

    def dry_run(
        self,
        *,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        temp_retention_days: int = TEMP_RETENTION_DAYS,
        max_scan_files: int = MAX_SCAN_FILES,
    ) -> dict[str, Any]:
        candidates = self.find_candidates(
            retention_days=retention_days,
            temp_retention_days=temp_retention_days,
            max_scan_files=max_scan_files,
        )
        total_bytes = sum(candidate.size_bytes for candidate in candidates)
        payload = {
            "dry_run": True,
            "candidate_count": len(candidates),
            "total_candidate_bytes": total_bytes,
            "retention_days": retention_days,
            "temp_retention_days": temp_retention_days,
            "candidates": [candidate.as_dict() for candidate in candidates[:100]],
            "truncated": len(candidates) > 100,
        }
        logger.info("Storage cleanup dry-run completed", extra=payload)
        return payload

    def find_candidates(
        self,
        *,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        temp_retention_days: int = TEMP_RETENTION_DAYS,
        max_scan_files: int = MAX_SCAN_FILES,
    ) -> list[CleanupCandidate]:
        referenced_keys = {
            str(key).strip()
            for key in self.db.scalars(select(LoadDocument.storage_key)).all()
            if str(key).strip()
        }
        now = datetime.now(timezone.utc)
        orphan_cutoff = now - timedelta(days=max(retention_days, 1))
        temp_cutoff = now - timedelta(days=max(temp_retention_days, 1))
        candidates: list[CleanupCandidate] = []

        scanned = 0
        for path in self._iter_storage_files():
            scanned += 1
            if scanned > max_scan_files:
                logger.warning("Storage cleanup scan stopped at safety limit", extra={"max_scan_files": max_scan_files})
                break
            relative_path = str(path.relative_to(self.storage.root)).replace("\\", "/")
            if not self._is_managed_path(relative_path):
                continue
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if relative_path in referenced_keys:
                continue
            reason: str | None = None
            if relative_path.startswith(self.TEMP_PREFIXES) and modified_at < temp_cutoff:
                reason = "stale_temporary_file"
            elif modified_at < orphan_cutoff:
                reason = "orphaned_storage_file"
            if reason:
                candidates.append(
                    CleanupCandidate(
                        relative_path=relative_path,
                        reason=reason,
                        size_bytes=path.stat().st_size,
                        last_modified_at=modified_at.isoformat(),
                    )
                )
        return candidates

    def _iter_storage_files(self) -> list[Path]:
        if not self.storage.root.exists():
            return []
        return [path for path in self.storage.root.rglob("*") if path.is_file()]

    def _is_managed_path(self, relative_path: str) -> bool:
        return relative_path.startswith(self.MANAGED_PREFIXES)
