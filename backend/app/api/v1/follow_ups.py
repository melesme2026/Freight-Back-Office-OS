from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.followups.follow_up_service import FollowUpService

router = APIRouter()

READ_ROLES = {"owner", "admin", "ops", "ops_manager", "ops_agent", "billing", "billing_admin", "viewer", "support", "support_agent"}
WRITE_ROLES = {"owner", "admin", "ops", "ops_manager", "ops_agent", "billing", "billing_admin"}


class SnoozeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    until: datetime


def _service(db: Session) -> FollowUpService:
    return FollowUpService(db)


def _org_id(payload: dict[str, Any]) -> str:
    return str(payload.get("organization_id") or "")


def _actor(payload: dict[str, Any]) -> str | None:
    for key in ("staff_user_id", "sub"):
        value = payload.get(key)
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return None


def _authorize(payload: dict[str, Any], *, write: bool) -> None:
    role = str(payload.get("role") or "").lower()
    if write and role not in WRITE_ROLES:
        raise ForbiddenError("You do not have permission to update follow-ups")
    if not write and role not in READ_ROLES and role not in WRITE_ROLES:
        raise ForbiddenError("You do not have permission to view follow-ups")


def _serialize(task: Any) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "organization_id": str(task.organization_id),
        "load_id": str(task.load_id),
        "submission_packet_id": str(task.submission_packet_id) if task.submission_packet_id else None,
        "payment_record_id": str(task.payment_record_id) if task.payment_record_id else None,
        "task_type": getattr(task.task_type, "value", str(task.task_type)),
        "status": getattr(task.status, "value", str(task.status)),
        "priority": getattr(task.priority, "value", str(task.priority)),
        "title": task.title,
        "description": task.description,
        "recommended_action": task.recommended_action,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "snoozed_until": task.snoozed_until.isoformat() if task.snoozed_until else None,
    }


@router.get("/follow-ups", response_model=ApiResponse)
def list_followups(
    status: str | None = None,
    priority: str | None = None,
    task_type: str | None = None,
    due_before: datetime | None = None,
    load_id: str | None = None,
    assigned_to_me: bool = False,
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize(token_payload, write=False)
    actor_staff_user_id = _actor(token_payload) if assigned_to_me else None
    tasks = _service(db).list_followups(
        _org_id(token_payload),
        {
            "status": status,
            "priority": priority,
            "task_type": task_type,
            "due_before": due_before,
            "load_id": load_id,
            "assigned_to_staff_user_id": actor_staff_user_id,
        },
    )
    return ApiResponse(data=[_serialize(task) for task in tasks])


@router.post("/follow-ups/generate", response_model=ApiResponse)
def generate_followups_for_org(db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize(token_payload, write=True)
    summary = _service(db).generate_followups_for_org(_org_id(token_payload))
    return ApiResponse(data=summary)


@router.post("/loads/{load_id}/follow-ups/generate", response_model=ApiResponse)
def generate_followups_for_load(load_id: str, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize(token_payload, write=True)
    tasks = _service(db).generate_followups_for_load(load_id, _org_id(token_payload))
    return ApiResponse(data=[_serialize(task) for task in tasks])


@router.post("/follow-ups/{task_id}/complete", response_model=ApiResponse)
def complete_followup(task_id: str, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize(token_payload, write=True)
    task = _service(db).complete_followup(task_id, _org_id(token_payload), _actor(token_payload))
    return ApiResponse(data=_serialize(task))


@router.post("/follow-ups/{task_id}/snooze", response_model=ApiResponse)
def snooze_followup(task_id: str, payload: SnoozeRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize(token_payload, write=True)
    task = _service(db).snooze_followup(task_id, _org_id(token_payload), payload.until, _actor(token_payload))
    return ApiResponse(data=_serialize(task))


@router.post("/follow-ups/{task_id}/cancel", response_model=ApiResponse)
def cancel_followup(task_id: str, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize(token_payload, write=True)
    task = _service(db).cancel_followup(task_id, _org_id(token_payload), _actor(token_payload))
    return ApiResponse(data=_serialize(task))
