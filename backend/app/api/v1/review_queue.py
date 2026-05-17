from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.review.human_review_service import HumanReviewService
from app.services.review.review_queue_service import ReviewQueueService
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)

router = APIRouter()
logger = logging.getLogger(__name__)


def _log_endpoint_timing(
    *,
    endpoint: str,
    started_at: float,
    organization_id: object | None = None,
    result_count: int | None = None,
    category: str = "ok",
) -> int:
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Endpoint timing",
        extra={
            "endpoint": endpoint,
            "organization_id": str(organization_id) if organization_id is not None else None,
            "duration_ms": elapsed_ms,
            "result_count": result_count,
            "category": category,
        },
    )
    return elapsed_ms

def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _to_decimal_string(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _serialize_extracted_field(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "document_id": str(item.document_id),
        "load_id": str(item.load_id) if item.load_id else None,
        "field_name": item.field_name,
        "field_value_text": item.field_value_text,
        "field_value_number": _to_decimal_string(item.field_value_number),
        "field_value_date": _to_iso_or_none(item.field_value_date),
        "field_value_json": item.field_value_json,
        "confidence_score": _to_decimal_string(item.confidence_score),
        "is_human_corrected": item.is_human_corrected,
        "corrected_by_staff_user_id": (
            str(item.corrected_by_staff_user_id) if item.corrected_by_staff_user_id else None
        ),
        "corrected_at": _to_iso_or_none(item.corrected_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _serialize_validation_issue(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "load_id": str(item.load_id),
        "document_id": str(item.document_id) if item.document_id else None,
        "rule_code": item.rule_code,
        "severity": _enum_to_string(item.severity),
        "title": item.title,
        "description": item.description,
        "is_blocking": item.is_blocking,
        "is_resolved": item.is_resolved,
        "resolved_by_staff_user_id": (
            str(item.resolved_by_staff_user_id) if item.resolved_by_staff_user_id else None
        ),
        "resolved_at": _to_iso_or_none(item.resolved_at),
        "resolution_notes": item.resolution_notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _serialize_reviewed_load(item: Any) -> dict[str, Any]:
    reviewed_by_user = getattr(item, "last_reviewed_by_user", None)

    return {
        "id": str(item.id),
        "last_reviewed_by": str(item.last_reviewed_by) if item.last_reviewed_by else None,
        "last_reviewed_by_name": (
            getattr(reviewed_by_user, "full_name", None) if reviewed_by_user else None
        ),
        "last_reviewed_at": _to_iso_or_none(item.last_reviewed_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


class CorrectExtractedFieldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_value_text: str | None = None
    field_value_number: str | None = None
    field_value_date: str | None = None
    field_value_json: dict[str, Any] | list[Any] | None = None


class ResolveValidationIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str | None = None


class MarkLoadReviewedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


@router.get("/review-queue", response_model=ApiResponse)
def get_review_queue(
    *,
    organization_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    started_at = time.perf_counter()
    service = ReviewQueueService(db)
    result = service.get_review_queue(
        organization_id=_uuid_to_str(effective_org_id),
        page=page,
        page_size=page_size,
    )

    elapsed_ms = _log_endpoint_timing(
        endpoint="review_queue",
        started_at=started_at,
        organization_id=effective_org_id,
        result_count=len(result["items"]),
    )

    return ApiResponse(
        data=result["items"],
        meta={
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "elapsed_ms": elapsed_ms,
            "hydration_mode": "issue_first",
        },
        error=None,
    )


@router.post("/review-queue/fields/{field_id}/correct", response_model=ApiResponse)
def correct_extracted_field(
    field_id: uuid.UUID,
    payload: CorrectExtractedFieldRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    reviewer_staff_user_id = str(token_payload.get("sub") or "").strip()

    service = HumanReviewService(db)
    item = service.correct_extracted_field(
        field_id=str(field_id),
        organization_id=str(token_org_id),
        staff_user_id=reviewer_staff_user_id,
        field_value_text=_normalize_optional_text(payload.field_value_text),
        field_value_number=_normalize_optional_text(payload.field_value_number),
        field_value_date=_normalize_optional_text(payload.field_value_date),
        field_value_json=payload.field_value_json,
    )

    db.commit()

    return ApiResponse(
        data=_serialize_extracted_field(item),
        meta={},
        error=None,
    )


@router.post("/review-queue/issues/{issue_id}/resolve", response_model=ApiResponse)
def resolve_validation_issue(
    issue_id: uuid.UUID,
    payload: ResolveValidationIssueRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    reviewer_staff_user_id = str(token_payload.get("sub") or "").strip()

    service = HumanReviewService(db)
    item = service.resolve_validation_issue(
        issue_id=str(issue_id),
        organization_id=str(token_org_id),
        staff_user_id=reviewer_staff_user_id,
        resolution_notes=_normalize_optional_text(payload.resolution_notes),
    )

    db.commit()

    return ApiResponse(
        data=_serialize_validation_issue(item),
        meta={},
        error=None,
    )


@router.post("/review-queue/loads/{load_id}/mark-reviewed", response_model=ApiResponse)
def mark_load_reviewed(
    load_id: uuid.UUID,
    payload: MarkLoadReviewedRequest | None = None,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ = payload
    reviewer_staff_user_id = str(token_payload.get("sub") or "").strip()
    token_org_id = token_payload.get("organization_id")

    service = HumanReviewService(db)
    item = service.mark_load_reviewed(
        load_id=str(load_id),
        organization_id=str(token_org_id),
        staff_user_id=reviewer_staff_user_id,
    )

    db.commit()

    return ApiResponse(
        data=_serialize_reviewed_load(item),
        meta={},
        error=None,
    )


@router.get("/review-queue/loads/{load_id}/context", response_model=ApiResponse)
def get_load_review_context(
    load_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")

    started_at = time.perf_counter()
    service = ReviewQueueService(db)
    try:
        item = service.get_load_review_context(
            organization_id=str(token_org_id),
            load_id=str(load_id),
        )
    except ValueError as exc:
        raise UnauthorizedError("Load is not in authenticated organization") from exc

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Review queue load context endpoint completed",
        extra={
            "load_id": str(load_id),
            "organization_id": str(token_org_id),
            "elapsed_ms": elapsed_ms,
        },
    )

    return ApiResponse(
        data=item,
        meta={"elapsed_ms": elapsed_ms},
        error=None,
    )
