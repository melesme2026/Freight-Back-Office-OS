from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums.load_status import LoadStatus
from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository


class LoadSummaryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)
        self.validation_repo = ValidationRepository(db)

    def summarize_load(self, *, load_id: str) -> dict[str, Any]:
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            return {
                "load_id": load_id,
                "exists": False,
            }

        validation_issues, _ = self.validation_repo.list(
            load_id=load.id,
            page=1,
            page_size=500,
        )

        blocking_issue_count = sum(1 for issue in validation_issues if issue.is_blocking)
        unresolved_issue_count = sum(1 for issue in validation_issues if not issue.is_resolved)
        warning_issue_count = sum(
            1
            for issue in validation_issues
            if str(issue.severity) in {"warning", "ValidationSeverity.WARNING"}
        )

        normalized_status = self._normalize_load_status(load.status)

        return {
            "load_id": str(load.id),
            "exists": True,
            "status": str(load.status),
            "processing_status": str(load.processing_status),
            "load_number": load.load_number,
            "invoice_number": load.invoice_number,
            "gross_amount": self._decimal_to_str(load.gross_amount),
            "currency_code": load.currency_code,
            "documents_complete": load.documents_complete,
            "has_ratecon": load.has_ratecon,
            "has_bol": load.has_bol,
            "has_invoice": load.has_invoice,
            "extraction_confidence_avg": self._decimal_to_str(load.extraction_confidence_avg),
            "blocking_issue_count": blocking_issue_count,
            "warning_issue_count": warning_issue_count,
            "unresolved_issue_count": unresolved_issue_count,
            "is_ready_for_submission": (
                normalized_status in {LoadStatus.READY_TO_SUBMIT}
                and blocking_issue_count == 0
            ),
        }

    @staticmethod
    def _decimal_to_str(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(Decimal(str(value)), "f")

    @staticmethod
    def _normalize_load_status(value: Any) -> LoadStatus | None:
        if isinstance(value, LoadStatus):
            return value

        normalized = str(value or "").strip().lower()

        aliases: dict[str, LoadStatus] = {
            "new": LoadStatus.NEW,
            "docs_received": LoadStatus.DOCS_RECEIVED,
            "needs_review": LoadStatus.NEEDS_REVIEW,
            "ready_to_submit": LoadStatus.READY_TO_SUBMIT,
            "submitted_to_broker": LoadStatus.SUBMITTED_TO_BROKER,
            "waiting_on_broker": LoadStatus.WAITING_ON_BROKER,
            "submitted_to_factoring": LoadStatus.SUBMITTED_TO_FACTORING,
            "waiting_on_funding": LoadStatus.WAITING_ON_FUNDING,
            "funded": LoadStatus.FUNDED,
            "paid": LoadStatus.PAID,
            "exception": LoadStatus.EXCEPTION,
            "archived": LoadStatus.ARCHIVED,
        }

        return aliases.get(normalized)
