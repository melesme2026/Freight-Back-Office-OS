from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.review.human_review_service import HumanReviewService
from app.services.review.review_queue_service import ReviewQueueService


router = APIRouter()


@router.get("/review-queue", response_model=ApiResponse)
def get_review_queue(
    *,
    organization_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    if organization_id:
        try:
            uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    service = ReviewQueueService(db)
    result = service.get_review_queue(
        organization_id=organization_id,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=result["items"],
        meta={
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
        },
        error=None,
    )


@router.post("/review-queue/fields/{field_id}/correct", response_model=ApiResponse)
def correct_extracted_field(
    field_id: str,
    *,
    staff_user_id: str,
    field_value_text: str | None = None,
    field_value_number: str | None = None,
    field_value_date: str | None = None,
    field_value_json: dict | list | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(field_id)
        uuid.UUID(staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={"field_id": field_id, "staff_user_id": staff_user_id},
        ) from exc

    service = HumanReviewService(db)
    item = service.correct_extracted_field(
        field_id=field_id,
        staff_user_id=staff_user_id,
        field_value_text=field_value_text,
        field_value_number=field_value_number,
        field_value_date=field_value_date,
        field_value_json=field_value_json,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "document_id": str(item.document_id),
            "load_id": str(item.load_id) if item.load_id else None,
            "field_name": item.field_name,
            "field_value_text": item.field_value_text,
            "field_value_number": str(item.field_value_number) if item.field_value_number is not None else None,
            "field_value_date": item.field_value_date.isoformat() if item.field_value_date else None,
            "field_value_json": item.field_value_json,
            "confidence_score": str(item.confidence_score),
            "is_human_corrected": item.is_human_corrected,
            "corrected_by_staff_user_id": str(item.corrected_by_staff_user_id) if item.corrected_by_staff_user_id else None,
            "corrected_at": item.corrected_at.isoformat() if item.corrected_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/review-queue/issues/{issue_id}/resolve", response_model=ApiResponse)
def resolve_validation_issue(
    issue_id: str,
    *,
    staff_user_id: str,
    resolution_notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(issue_id)
        uuid.UUID(staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={"issue_id": issue_id, "staff_user_id": staff_user_id},
        ) from exc

    service = HumanReviewService(db)
    item = service.resolve_validation_issue(
        issue_id=issue_id,
        staff_user_id=staff_user_id,
        resolution_notes=resolution_notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "load_id": str(item.load_id),
            "document_id": str(item.document_id) if item.document_id else None,
            "rule_code": item.rule_code,
            "severity": str(item.severity),
            "title": item.title,
            "description": item.description,
            "is_blocking": item.is_blocking,
            "is_resolved": item.is_resolved,
            "resolved_by_staff_user_id": str(item.resolved_by_staff_user_id) if item.resolved_by_staff_user_id else None,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "resolution_notes": item.resolution_notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/review-queue/loads/{load_id}/mark-reviewed", response_model=ApiResponse)
def mark_load_reviewed(
    load_id: str,
    *,
    staff_user_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(load_id)
        uuid.UUID(staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={"load_id": load_id, "staff_user_id": staff_user_id},
        ) from exc

    service = HumanReviewService(db)
    item = service.mark_load_reviewed(
        load_id=load_id,
        staff_user_id=staff_user_id,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "last_reviewed_by": str(item.last_reviewed_by) if item.last_reviewed_by else None,
            "last_reviewed_at": item.last_reviewed_at.isoformat() if item.last_reviewed_at else None,
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )