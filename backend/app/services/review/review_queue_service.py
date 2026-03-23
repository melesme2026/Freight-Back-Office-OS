from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository


class ReviewQueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)
        self.validation_repo = ValidationRepository(db)

    def get_review_queue(
        self,
        *,
        organization_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        loads, total = self.load_repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
        )

        items: list[dict] = []

        for load in loads:
            issues, _ = self.validation_repo.list(
                load_id=load.id,
                page=1,
                page_size=500,
            )

            blocking_issue_count = sum(
                1 for issue in issues if issue.is_blocking and not issue.is_resolved
            )
            warning_issue_count = sum(
                1
                for issue in issues
                if str(issue.severity) in {"warning", "ValidationSeverity.WARNING"}
                and not issue.is_resolved
            )

            if blocking_issue_count == 0 and warning_issue_count == 0:
                continue

            items.append(
                {
                    "load_id": str(load.id),
                    "driver_name": getattr(load.driver, "full_name", None),
                    "load_number": load.load_number,
                    "status": str(load.status),
                    "blocking_issue_count": blocking_issue_count,
                    "warning_issue_count": warning_issue_count,
                    "extraction_confidence_avg": (
                        float(load.extraction_confidence_avg)
                        if load.extraction_confidence_avg is not None
                        else None
                    ),
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }