from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.validation_issue import ValidationIssue


class ValidationRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, validation_issue: ValidationIssue) -> ValidationIssue:
        self.db.add(validation_issue)
        self.db.flush()
        self.db.refresh(validation_issue)
        return validation_issue

    def create_many(self, validation_issues: list[ValidationIssue]) -> list[ValidationIssue]:
        if not validation_issues:
            return []

        self.db.add_all(validation_issues)
        self.db.flush()

        for item in validation_issues:
            self.db.refresh(item)

        return validation_issues

    def get_by_id(
        self,
        issue_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> ValidationIssue | None:
        normalized_issue_id = self._normalize_uuid(issue_id, field_name="issue_id")

        stmt = select(ValidationIssue).where(ValidationIssue.id == normalized_issue_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        document_id: uuid.UUID | str | None = None,
        severity: ValidationSeverity | None = None,
        is_resolved: bool | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[ValidationIssue], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_load_id = (
            self._normalize_uuid(load_id, field_name="load_id")
            if load_id is not None
            else None
        )
        normalized_document_id = (
            self._normalize_uuid(document_id, field_name="document_id")
            if document_id is not None
            else None
        )

        stmt = select(ValidationIssue)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ValidationIssue)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(ValidationIssue.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(ValidationIssue.organization_id == normalized_organization_id)

        if normalized_load_id is not None:
            stmt = stmt.where(ValidationIssue.load_id == normalized_load_id)
            count_stmt = count_stmt.where(ValidationIssue.load_id == normalized_load_id)

        if normalized_document_id is not None:
            stmt = stmt.where(ValidationIssue.document_id == normalized_document_id)
            count_stmt = count_stmt.where(ValidationIssue.document_id == normalized_document_id)

        if severity is not None:
            stmt = stmt.where(ValidationIssue.severity == severity)
            count_stmt = count_stmt.where(ValidationIssue.severity == severity)

        if is_resolved is not None:
            stmt = stmt.where(ValidationIssue.is_resolved == is_resolved)
            count_stmt = count_stmt.where(ValidationIssue.is_resolved == is_resolved)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(ValidationIssue.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def count_blocking_unresolved_for_load(self, load_id: uuid.UUID | str) -> int:
        normalized_load_id = self._normalize_uuid(load_id, field_name="load_id")

        stmt = (
            select(func.count())
            .select_from(ValidationIssue)
            .where(
                ValidationIssue.load_id == normalized_load_id,
                ValidationIssue.is_blocking.is_(True),
                ValidationIssue.is_resolved.is_(False),
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def update(self, validation_issue: ValidationIssue) -> ValidationIssue:
        self.db.add(validation_issue)
        self.db.flush()
        self.db.refresh(validation_issue)
        return validation_issue

    def delete(self, validation_issue: ValidationIssue) -> None:
        self.db.delete(validation_issue)
        self.db.flush()

    def _apply_related(
        self,
        stmt: Select[tuple[ValidationIssue]],
    ) -> Select[tuple[ValidationIssue]]:
        return stmt.options(
            selectinload(ValidationIssue.load),
            selectinload(ValidationIssue.document),
            selectinload(ValidationIssue.resolved_by_user),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc