from __future__ import annotations

import uuid
from typing import Any

from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.load import Load
from app.domain.models.validation_issue import ValidationIssue
from app.repositories.load_repo import LoadRepository
from sqlalchemy import case, desc, distinct, func, select
from sqlalchemy.orm import Session, noload, selectinload


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

        return self._build_queue_item_from_issues(
            load=load, unresolved_issues=unresolved_issues
        )

    def _build_queue_item_from_issues(
        self, *, load: Any, unresolved_issues: list[ValidationIssue]
    ) -> dict[str, Any]:
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
            "driver_id": (
                str(load.driver_id) if getattr(load, "driver_id", None) else None
            ),
            "driver_name": getattr(driver, "full_name", None),
            "customer_account_id": (
                str(load.customer_account_id)
                if getattr(load, "customer_account_id", None)
                else None
            ),
            "customer_account_name": (
                getattr(customer_account, "account_name", None)
                if customer_account
                else None
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
        if load is None or str(getattr(load, "organization_id", "")) != str(
            organization_id
        ):
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
        """Return a paged review queue without hydrating organization-wide loads.

        The old implementation loaded up to every load plus documents/workflow
        relationships and then filtered in Python. This query is issue-first:
        unresolved validation issues are the queue trigger, org scope is applied
        in SQL, and only the page of affected loads is hydrated.
        """
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.load_repo.MAX_PAGE_SIZE)
        offset = (normalized_page - 1) * normalized_page_size

        org_uuid = (
            uuid.UUID(str(organization_id)) if organization_id is not None else None
        )
        filters = [ValidationIssue.is_resolved.is_(False)]
        if org_uuid is not None:
            filters.append(ValidationIssue.organization_id == org_uuid)

        total_stmt = select(func.count(distinct(ValidationIssue.load_id))).where(
            *filters
        )
        total = int(self.db.scalar(total_stmt) or 0)
        if total == 0:
            return {
                "items": [],
                "total": 0,
                "page": normalized_page,
                "page_size": normalized_page_size,
            }

        high_priority = func.max(
            case(
                (
                    (ValidationIssue.is_blocking.is_(True))
                    | (
                        ValidationIssue.severity.in_(
                            [
                                ValidationSeverity.CRITICAL,
                                ValidationSeverity.ERROR,
                            ]
                        )
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("high_priority")
        latest_issue_at = func.max(ValidationIssue.created_at).label("latest_issue_at")

        page_rows = self.db.execute(
            select(ValidationIssue.load_id, high_priority, latest_issue_at)
            .where(*filters)
            .group_by(ValidationIssue.load_id)
            .order_by(
                desc(high_priority), desc(latest_issue_at), ValidationIssue.load_id
            )
            .offset(offset)
            .limit(normalized_page_size)
        ).all()
        load_ids = [row.load_id for row in page_rows]
        if not load_ids:
            return {
                "items": [],
                "total": total,
                "page": normalized_page,
                "page_size": normalized_page_size,
            }

        loads = list(
            self.db.scalars(
                select(Load)
                .options(
                    noload("*"),
                    selectinload(Load.driver),
                    selectinload(Load.customer_account),
                )
                .where(Load.id.in_(load_ids))
            ).all()
        )
        loads_by_id = {load.id: load for load in loads}

        issues = list(
            self.db.scalars(
                select(ValidationIssue)
                .options(noload("*"))
                .where(
                    ValidationIssue.load_id.in_(load_ids),
                    ValidationIssue.is_resolved.is_(False),
                )
            ).all()
        )
        issues_by_load_id: dict[Any, list[ValidationIssue]] = {}
        for issue in issues:
            issues_by_load_id.setdefault(issue.load_id, []).append(issue)

        queue_items = []
        for load_id in load_ids:
            load = loads_by_id.get(load_id)
            load_issues = issues_by_load_id.get(load_id, [])
            if load is None or not load_issues:
                continue
            queue_items.append(
                self._build_queue_item_from_issues(
                    load=load, unresolved_issues=load_issues
                )
            )

        return {
            "items": queue_items,
            "total": total,
            "page": normalized_page,
            "page_size": normalized_page_size,
        }
