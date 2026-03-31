from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.load_repo import LoadRepository


class ReviewQueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)

    @staticmethod
    def _normalize_severity(value: object) -> str:
        if value is None:
            return "unknown"

        raw = str(value).strip().lower()

        if "." in raw:
            raw = raw.split(".")[-1]

        if raw in {"critical", "error", "high"}:
            return "high"

        if raw in {"warning", "medium"}:
            return "medium"

        if raw in {"info", "informational", "low"}:
            return "low"

        return raw or "unknown"

    @staticmethod
    def _issue_sort_rank(issue: object) -> tuple[int, str]:
        is_blocking = bool(getattr(issue, "is_blocking", False))
        severity = ReviewQueueService._normalize_severity(
            getattr(issue, "severity", None)
        )

        if is_blocking or severity == "high":
            priority = 0
        elif severity == "medium":
            priority = 1
        else:
            priority = 2

        title = str(getattr(issue, "title", "") or "").strip().lower()
        return (priority, title)

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
            include_related=True,
        )

        items: list[dict] = []

        for load in loads:
            load_issues = list(getattr(load, "validation_issues", []) or [])

            unresolved_issues = [
                issue for issue in load_issues if not getattr(issue, "is_resolved", False)
            ]

            if not unresolved_issues:
                continue

            sorted_issues = sorted(unresolved_issues, key=self._issue_sort_rank)
            primary_issue = sorted_issues[0]

            issue_count = len(unresolved_issues)
            blocking_issue_count = sum(
                1 for issue in unresolved_issues if getattr(issue, "is_blocking", False)
            )
            warning_issue_count = sum(
                1
                for issue in unresolved_issues
                if self._normalize_severity(getattr(issue, "severity", None)) == "medium"
            )

            primary_title = str(getattr(primary_issue, "title", "") or "").strip()
            primary_description = str(
                getattr(primary_issue, "description", "") or ""
            ).strip()

            driver = getattr(load, "driver", None)

            items.append(
                {
                    "load_id": str(load.id),
                    "load_number": load.load_number,
                    "status": str(load.status),
                    "driver_name": getattr(driver, "full_name", None),
                    "issue_count": issue_count,
                    "blocking_issue_count": blocking_issue_count,
                    "warning_issue_count": warning_issue_count,
                    "primary_issue": primary_title
                    or primary_description
                    or "Review required",
                    "severity": self._normalize_severity(
                        getattr(primary_issue, "severity", None)
                    ),
                    "primary_issue_is_blocking": bool(
                        getattr(primary_issue, "is_blocking", False)
                    ),
                    "primary_issue_rule_code": getattr(primary_issue, "rule_code", None),
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