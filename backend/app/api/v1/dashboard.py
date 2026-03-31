from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.dependencies import get_db_session
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.validation_issue import ValidationIssue
from app.schemas.common import ApiResponse


router = APIRouter()


def _scalar_count(db: Session, stmt: Select[tuple[int]]) -> int:
    return int(db.execute(stmt).scalar_one())


def _apply_optional_org_filter(
    stmt: Select,
    *,
    organization_id: uuid.UUID | None,
    model: type,
) -> Select:
    if organization_id is None:
        return stmt
    return stmt.where(model.organization_id == organization_id)


@router.get("/dashboard", response_model=ApiResponse)
def get_dashboard(
    *,
    organization_id: uuid.UUID | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    loads_total_stmt = _apply_optional_org_filter(
        select(func.count()).select_from(Load),
        organization_id=organization_id,
        model=Load,
    )

    loads_needing_review_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == "needs_review"),
        organization_id=organization_id,
        model=Load,
    )

    loads_validated_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == "validated"),
        organization_id=organization_id,
        model=Load,
    )

    loads_paid_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == "paid"),
        organization_id=organization_id,
        model=Load,
    )

    documents_pending_processing_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(LoadDocument)
        .where(LoadDocument.processing_status != "completed"),
        organization_id=organization_id,
        model=LoadDocument,
    )

    critical_validation_issues_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(ValidationIssue)
        .where(ValidationIssue.is_resolved.is_(False))
        .where(ValidationIssue.severity == "critical"),
        organization_id=organization_id,
        model=ValidationIssue,
    )

    return ApiResponse(
        data={
            "loads_total": _scalar_count(db, loads_total_stmt),
            "loads_needing_review": _scalar_count(db, loads_needing_review_stmt),
            "loads_validated": _scalar_count(db, loads_validated_stmt),
            "loads_paid": _scalar_count(db, loads_paid_stmt),
            "documents_pending_processing": _scalar_count(
                db, documents_pending_processing_stmt
            ),
            "critical_validation_issues": _scalar_count(
                db, critical_validation_issues_stmt
            ),
        },
        meta={},
        error=None,
    )