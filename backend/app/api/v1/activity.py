from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.audit.activity_service import ActivityService, organization_id_from_token

router = APIRouter(prefix="/activity")


@router.get("", response_model=ApiResponse)
def list_activity(
    *,
    limit: int = Query(default=25, ge=1, le=100),
    entity_type: str | None = Query(default=None, max_length=100),
    action: str | None = Query(default=None, max_length=100),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    organization_id = organization_id_from_token(token_payload)
    items, meta = ActivityService(db).list_recent_activity(
        organization_id=organization_id,
        token_payload=token_payload,
        limit=limit,
        entity_type=entity_type,
        action=action,
    )
    return ApiResponse(data=items, meta=meta, error=None)
