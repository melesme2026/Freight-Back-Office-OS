from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.storage.cleanup_service import StorageCleanupService

router = APIRouter(prefix="/operations")


def _require_admin(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in {"owner", "admin", "ops_manager", "support"}:
        raise ForbiddenError("You do not have permission to run operational safety checks")


@router.get("/storage-cleanup/dry-run", response_model=ApiResponse)
def storage_cleanup_dry_run(
    *,
    retention_days: int = Query(default=30, ge=7, le=365),
    temp_retention_days: int = Query(default=2, ge=1, le=30),
    max_scan_files: int = Query(default=5000, ge=100, le=25000),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _require_admin(token_payload)
    result = StorageCleanupService(db).dry_run(
        retention_days=retention_days,
        temp_retention_days=temp_retention_days,
        max_scan_files=max_scan_files,
    )
    return ApiResponse(data=result, meta={"destructive": False}, error=None)
