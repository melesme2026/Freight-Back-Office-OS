from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.operations.command_center_service import DispatcherCommandCenterService
from app.services.storage.cleanup_service import StorageCleanupService

router = APIRouter(prefix="/operations")


def _require_admin(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in {"owner", "admin", "ops_manager", "support"}:
        raise ForbiddenError("You do not have permission to run operational safety checks")


def _require_command_center_access(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in {"owner", "admin", "ops_manager", "ops_agent", "billing_admin", "support", "support_agent"}:
        raise ForbiddenError("Drivers cannot access dispatcher command center operations views")


@router.get("/command-center", response_model=ApiResponse)
def get_dispatcher_command_center(
    *,
    organization_id: str | None = None,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _require_command_center_access(token_payload)

    token_org_id = str(token_payload.get("organization_id") or "")
    effective_org_id = organization_id or token_org_id
    if not token_org_id or str(effective_org_id) != token_org_id:
        raise ForbiddenError("organization_id does not match authenticated organization")

    data = DispatcherCommandCenterService(db).get_command_center(org_id=effective_org_id)
    return ApiResponse(data=data, meta={"organization_id": effective_org_id}, error=None)


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
