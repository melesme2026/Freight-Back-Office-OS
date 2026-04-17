from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import get_current_token_payload
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.validation_issue import ValidationIssue
from app.schemas.common import ApiResponse


router = APIRouter()


def _scalar_count(db: Session, stmt: Select[tuple[int]]) -> int:
    return int(db.execute(stmt).scalar_one())


def _apply_optional_org_filter(
    stmt: Select[tuple[int]],
    *,
    organization_id: uuid.UUID | None,
    model: type[Load] | type[LoadDocument] | type[ValidationIssue],
) -> Select[tuple[int]]:
    if organization_id is None:
        return stmt
    return stmt.where(model.organization_id == organization_id)


@router.get("/dashboard", response_model=ApiResponse)
def get_dashboard(
    *,
    organization_id: uuid.UUID | None = None,
    token_payload: dict[str, object] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    loads_total_stmt = _apply_optional_org_filter(
        select(func.count()).select_from(Load),
        organization_id=effective_org_id,
        model=Load,
    )

    loads_needing_review_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == LoadStatus.NEEDS_REVIEW),
        organization_id=effective_org_id,
        model=Load,
    )

    loads_ready_to_submit_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == LoadStatus.READY_TO_SUBMIT),
        organization_id=effective_org_id,
        model=Load,
    )

    loads_paid_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(Load)
        .where(Load.status == LoadStatus.PAID),
        organization_id=effective_org_id,
        model=Load,
    )

    documents_pending_processing_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(LoadDocument)
        .where(LoadDocument.processing_status != ProcessingStatus.COMPLETED),
        organization_id=effective_org_id,
        model=LoadDocument,
    )

    critical_validation_issues_stmt = _apply_optional_org_filter(
        select(func.count())
        .select_from(ValidationIssue)
        .where(ValidationIssue.is_resolved.is_(False))
        .where(ValidationIssue.severity == ValidationSeverity.CRITICAL),
        organization_id=effective_org_id,
        model=ValidationIssue,
    )

    return ApiResponse(
        data={
            "loads_total": _scalar_count(db, loads_total_stmt),
            "loads_needing_review": _scalar_count(db, loads_needing_review_stmt),
            "loads_validated": _scalar_count(db, loads_ready_to_submit_stmt),
            "loads_paid": _scalar_count(db, loads_paid_stmt),
            "documents_pending_processing": _scalar_count(
                db,
                documents_pending_processing_stmt,
            ),
            "critical_validation_issues": _scalar_count(
                db,
                critical_validation_issues_stmt,
            ),
        },
        meta={},
        error=None,
    )
