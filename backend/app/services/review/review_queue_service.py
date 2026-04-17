from __future__ import annotations

from typing import Any

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
    def _normalize_status(value: object) -> str | None:
        if value is None:
            return None

        enum_value = getattr(value, "value", None)
        if isinstance(enum_value, str):
            return enum_value

        normalized = str(value).strip()
        if "." in normalized:
            normalized = normalized.split(".")[-1]

        return normalized.lower() or None

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

    @staticmethod
    def _safe_float(value: object | None) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_queue_item(self, load: Any) -> dict[str, Any] | None:
        load_issues = list(getattr(load, "validation_issues", []) or [])

        unresolved_issues = [
            issue for issue in load_issues if not getattr(issue, "is_resolved", False)
        ]

        if not unresolved_issues:
            return None

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
        customer_account = getattr(load, "customer_account", None)

        return {
            "load_id": str(load.id),
            "load_number": load.load_number,
            "status": self._normalize_status(getattr(load, "status", None)),
            "driver_id": str(load.driver_id) if getattr(load, "driver_id", None) else None,
            "driver_name": getattr(driver, "full_name", None),
            "customer_account_id": (
                str(load.customer_account_id)
                if getattr(load, "customer_account_id", None)
                else None
            ),
            "customer_account_name": (
                getattr(customer_account, "account_name", None) if customer_account else None
            ),
            "issue_count": issue_count,
            "blocking_issue_count": blocking_issue_count,
            "warning_issue_count": warning_issue_count,
            "primary_issue": primary_title or primary_description or "Review required",
            "severity": self._normalize_severity(
                getattr(primary_issue, "severity", None)
            ),
            "primary_issue_is_blocking": bool(
                getattr(primary_issue, "is_blocking", False)
            ),
            "primary_issue_rule_code": getattr(primary_issue, "rule_code", None),
            "extraction_confidence_avg": self._safe_float(
                getattr(load, "extraction_confidence_avg", None)
            ),
            "last_reviewed_at": (
                load.last_reviewed_at.isoformat()
                if getattr(load, "last_reviewed_at", None) is not None
                else None
            ),
        }


    def get_load_review_context(
        self,
        *,
        organization_id: str,
        load_id: str,
    ) -> dict[str, Any]:
        load = self.load_repo.get_by_id(load_id, include_related=True)
        if load is None or str(getattr(load, "organization_id", "")) != str(organization_id):
            raise ValueError("Load not found")

        item = self._build_queue_item(load)
        if item is not None:
            return item

        return {
            "load_id": str(load.id),
            "load_number": load.load_number,
            "status": self._normalize_status(getattr(load, "status", None)),
            "issue_count": 0,
            "blocking_issue_count": 0,
            "warning_issue_count": 0,
            "primary_issue": None,
            "severity": "low",
            "primary_issue_is_blocking": False,
            "primary_issue_rule_code": None,
            "extraction_confidence_avg": self._safe_float(
                getattr(load, "extraction_confidence_avg", None)
            ),
            "last_reviewed_at": (
                load.last_reviewed_at.isoformat()
                if getattr(load, "last_reviewed_at", None) is not None
                else None
            ),
        }

    def get_review_queue(
        self,
        *,
        organization_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        # Review queue pagination must be based on filtered reviewable loads,
        # not raw load pages. Pull a broad related set first, then paginate queue items.
        loads, _ = self.load_repo.list(
            organization_id=organization_id,
            page=1,
            page_size=self.load_repo.MAX_PAGE_SIZE,
            include_related=True,
        )

        queue_items: list[dict[str, Any]] = []

        for load in loads:
            try:
                item = self._build_queue_item(load)
            except (TypeError, ValueError, AttributeError):
                continue

            if item is not None:
                queue_items.append(item)

        queue_items.sort(
            key=lambda item: (
                0 if item["blocking_issue_count"] > 0 or item["severity"] == "high" else 1,
                0 if item["severity"] == "medium" else 1,
                (item.get("load_number") or ""),
            )
        )

        total = len(queue_items)

        normalized_page = max(page, 1)
        normalized_page_size = max(page_size, 1)
        start = (normalized_page - 1) * normalized_page_size
        end = start + normalized_page_size

        paged_items = queue_items[start:end]

        return {
            "items": paged_items,
            "total": total,
            "page": normalized_page,
            "page_size": normalized_page_size,
        }