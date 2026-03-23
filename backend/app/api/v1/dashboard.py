from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.repositories.document_repo import DocumentRepository
from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.get("/dashboard", response_model=ApiResponse)
def get_dashboard(
    *,
    organization_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    parsed_organization_id = None
    if organization_id:
        try:
            parsed_organization_id = uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    load_repo = LoadRepository(db)
    document_repo = DocumentRepository(db)
    validation_repo = ValidationRepository(db)

    loads, _ = load_repo.list(
        organization_id=parsed_organization_id,
        page=1,
        page_size=10000,
    )
    documents, _ = document_repo.list(
        organization_id=parsed_organization_id,
        page=1,
        page_size=10000,
    )
    validation_issues, _ = validation_repo.list(
        organization_id=parsed_organization_id,
        page=1,
        page_size=10000,
    )

    loads_total = len(loads)
    loads_needing_review = sum(1 for item in loads if str(item.status) == "needs_review")
    loads_validated = sum(1 for item in loads if str(item.status) == "validated")
    loads_paid = sum(1 for item in loads if str(item.status) == "paid")
    documents_pending_processing = sum(
        1 for item in documents if str(item.processing_status) != "completed"
    )
    critical_validation_issues = sum(
        1
        for item in validation_issues
        if str(item.severity) in {"critical", "ValidationSeverity.CRITICAL"}
        and not item.is_resolved
    )

    return ApiResponse(
        data={
            "loads_total": loads_total,
            "loads_needing_review": loads_needing_review,
            "loads_validated": loads_validated,
            "loads_paid": loads_paid,
            "documents_pending_processing": documents_pending_processing,
            "critical_validation_issues": critical_validation_issues,
        },
        meta={},
        error=None,
    )