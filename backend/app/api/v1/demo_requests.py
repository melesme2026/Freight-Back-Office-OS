from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, RateLimitError, UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.domain.models.demo_request import DemoRequest
from app.schemas.common import ApiResponse
from app.schemas.demo_requests import (
    DEMO_REQUEST_ACCEPTED_STATUSES,
    DEMO_REQUEST_STATUSES,
    DemoRequestCreateRequest,
    DemoRequestPipelineUpdateRequest,
    DemoRequestStatusUpdateRequest,
    normalize_demo_request_status,
)
from app.services.notifications.operational_notification_service import (
    OperationalNotificationService,
)
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)

router = APIRouter()

DB_SESSION_DEPENDENCY = GET_DB_SESSION_DEPENDENCY
TOKEN_PAYLOAD_DEPENDENCY = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY
STATUS_FILTER_QUERY = Query(default=None, alias="status")
PAGE_QUERY = Query(default=1, ge=1)
PAGE_SIZE_QUERY = Query(default=50, ge=1, le=200)
SEARCH_QUERY = Query(default=None, min_length=1, max_length=255)

STAFF_DEMO_REQUEST_ROLES = {"owner", "admin", "staff", "ops_manager", "ops_agent", "support_agent"}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip[:64]
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()[:64]
    return (
        getattr(request.client, "host", None)[:64]
        if request.client and request.client.host
        else None
    )


def _user_agent(request: Request | None) -> str | None:
    value = request.headers.get("user-agent") if request is not None else None
    return _clean_text(value)[:512] if _clean_text(value) else None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _window_start(seconds: int) -> datetime:
    return _utc_now() - timedelta(seconds=seconds)


def _find_recent_duplicate(
    db: Session,
    *,
    payload: DemoRequestCreateRequest,
    source_ip: str | None,
    window_seconds: int,
) -> DemoRequest | None:
    cutoff = _window_start(window_seconds)
    stmt = (
        select(DemoRequest)
        .where(DemoRequest.created_at >= cutoff)
        .where(func.lower(DemoRequest.email) == str(payload.email).lower())
        .where(func.lower(DemoRequest.company) == payload.company.lower())
        .where(DemoRequest.full_name == payload.full_name)
        .order_by(DemoRequest.created_at.desc())
        .limit(1)
    )
    if source_ip:
        stmt = stmt.where(or_(DemoRequest.source_ip == source_ip, DemoRequest.source_ip.is_(None)))
    return db.scalar(stmt)


def _enforce_ip_rate_limit(db: Session, *, source_ip: str | None) -> None:
    if not source_ip:
        return
    settings = get_settings()
    cutoff = _window_start(settings.demo_request_rate_limit_window_seconds)
    count = (
        db.scalar(
            select(func.count(DemoRequest.id)).where(
                DemoRequest.source_ip == source_ip,
                DemoRequest.created_at >= cutoff,
            )
        )
        or 0
    )
    if int(count) >= settings.demo_request_rate_limit_max_per_ip:
        raise RateLimitError(
            "Too many demo requests submitted recently. Please wait and try again.",
            details={"retry_after_seconds": settings.demo_request_rate_limit_window_seconds},
        )


def _serialize_demo_request(item: DemoRequest) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "full_name": item.full_name,
        "email": item.email,
        "company": item.company,
        "phone": item.phone,
        "fleet_size": item.fleet_size,
        "message": item.message,
        "status": normalize_demo_request_status(item.status),
        "notes": item.notes,
        "next_follow_up_at": item.next_follow_up_at.isoformat() if item.next_follow_up_at else None,
        "source": "request_demo",
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _ensure_demo_request_staff(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in STAFF_DEMO_REQUEST_ROLES:
        raise UnauthorizedError("Authenticated staff role is required to manage demo requests")


@router.post("/demo-requests", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_demo_request(
    payload: DemoRequestCreateRequest,
    request: Request = None,  # type: ignore[assignment]
    db: Session = DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    settings = get_settings()
    source_ip = _client_ip(request)
    user_agent = _user_agent(request)

    duplicate = _find_recent_duplicate(
        db,
        payload=payload,
        source_ip=source_ip,
        window_seconds=settings.demo_request_duplicate_window_seconds,
    )
    if duplicate is not None:
        return ApiResponse(
            data={
                "id": str(duplicate.id),
                "status": duplicate.status,
                "message": "Demo request received.",
                "duplicate": True,
            }
        )

    _enforce_ip_rate_limit(db, source_ip=source_ip)

    item = DemoRequest(
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        company=payload.company,
        phone=payload.phone,
        fleet_size=payload.fleet_size,
        message=payload.message,
        status="new",
        source_ip=source_ip,
        user_agent=user_agent,
    )
    db.add(item)
    db.flush()
    try:
        OperationalNotificationService(db).demo_request_received(
            demo_request_id=str(item.id),
            full_name=item.full_name,
            email=item.email,
            company=item.company,
            phone=item.phone,
            fleet_size=item.fleet_size,
            message=item.message,
            status=item.status,
            submitted_at=item.created_at or _utc_now(),
        )
    except Exception:
        logger.exception(
            "Demo request notification failed", extra={"demo_request_id": str(item.id)}
        )
    db.commit()
    db.refresh(item)
    return ApiResponse(
        data={
            "id": str(item.id),
            "status": item.status,
            "message": "Demo request received.",
            "duplicate": False,
        }
    )


@router.get("/demo-requests", response_model=ApiResponse)
def list_demo_requests(
    *,
    status_filter: str | None = STATUS_FILTER_QUERY,
    page: int = PAGE_QUERY,
    page_size: int = PAGE_SIZE_QUERY,
    search: str | None = SEARCH_QUERY,
    token_payload: dict[str, Any] = TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ensure_demo_request_staff(token_payload)
    stmt = select(DemoRequest)
    count_stmt = select(func.count(DemoRequest.id))
    if not isinstance(status_filter, str):
        status_filter = None
    if not isinstance(search, str):
        search = None

    if status_filter:
        normalized_status = status_filter.strip().lower()
        if normalized_status not in DEMO_REQUEST_ACCEPTED_STATUSES:
            raise ValidationError(
                "Invalid demo request status",
                details={"allowed_statuses": sorted(DEMO_REQUEST_STATUSES)},
            )
        normalized_status = normalize_demo_request_status(normalized_status)
        if normalized_status == "lost":
            status_clause = DemoRequest.status.in_(["lost", "closed"])
        else:
            status_clause = DemoRequest.status == normalized_status
        stmt = stmt.where(status_clause)
        count_stmt = count_stmt.where(status_clause)

    if search:
        term = f"%{search.strip().lower()}%"
        search_clause = or_(
            func.lower(DemoRequest.full_name).like(term),
            func.lower(DemoRequest.company).like(term),
            func.lower(DemoRequest.email).like(term),
            func.lower(func.coalesce(DemoRequest.phone, "")).like(term),
        )
        stmt = stmt.where(search_clause)
        count_stmt = count_stmt.where(search_clause)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(DemoRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    metric_rows = db.execute(
        select(DemoRequest.status, func.count(DemoRequest.id)).group_by(DemoRequest.status)
    ).all()
    metrics = {status: 0 for status in sorted(DEMO_REQUEST_STATUSES)}
    for raw_status, count in metric_rows:
        status_key = normalize_demo_request_status(str(raw_status or "new"))
        if status_key in metrics:
            metrics[status_key] += int(count)

    return ApiResponse(
        data=[_serialize_demo_request(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": int(total), "metrics": metrics},
    )


@router.get("/demo-requests/{demo_request_id}", response_model=ApiResponse)
def get_demo_request(
    demo_request_id: uuid.UUID,
    token_payload: dict[str, Any] = TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ensure_demo_request_staff(token_payload)
    item = db.get(DemoRequest, demo_request_id)
    if item is None:
        raise NotFoundError(
            "Demo request not found", details={"demo_request_id": str(demo_request_id)}
        )
    return ApiResponse(data=_serialize_demo_request(item))


@router.patch("/demo-requests/{demo_request_id}", response_model=ApiResponse)
def update_demo_request_pipeline(
    demo_request_id: uuid.UUID,
    payload: DemoRequestPipelineUpdateRequest,
    token_payload: dict[str, Any] = TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ensure_demo_request_staff(token_payload)
    item = db.get(DemoRequest, demo_request_id)
    if item is None:
        raise NotFoundError(
            "Demo request not found", details={"demo_request_id": str(demo_request_id)}
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        item.status = update_data["status"]
    if "notes" in update_data:
        item.notes = update_data["notes"]
    if "next_follow_up_at" in update_data:
        item.next_follow_up_at = update_data["next_follow_up_at"]

    db.add(item)
    db.commit()
    db.refresh(item)
    return ApiResponse(data=_serialize_demo_request(item))


@router.patch("/demo-requests/{demo_request_id}/status", response_model=ApiResponse)
def update_demo_request_status(
    demo_request_id: uuid.UUID,
    payload: DemoRequestStatusUpdateRequest,
    token_payload: dict[str, Any] = TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ensure_demo_request_staff(token_payload)
    item = db.get(DemoRequest, demo_request_id)
    if item is None:
        raise NotFoundError(
            "Demo request not found", details={"demo_request_id": str(demo_request_id)}
        )
    item.status = payload.status
    db.add(item)
    db.commit()
    db.refresh(item)
    return ApiResponse(data=_serialize_demo_request(item))
