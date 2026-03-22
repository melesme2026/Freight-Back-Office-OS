from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.validation_issue import ValidationIssue


class ValidationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, validation_issue: ValidationIssue) -> ValidationIssue:
        self.db.add(validation_issue)
        self.db.flush()
        self.db.refresh(validation_issue)
        return validation_issue

    def create_many(self, validation_issues: list[ValidationIssue]) -> list[ValidationIssue]:
        self.db.add_all(validation_issues)
        self.db.flush()
        for item in validation_issues:
            self.db.refresh(item)
        return validation_issues

    def get_by_id(self, issue_id: uuid.UUID) -> ValidationIssue | None:
        stmt = select(ValidationIssue).where(ValidationIssue.id == issue_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        severity: ValidationSeverity | None = None,
        is_resolved: bool | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[ValidationIssue], int]:
        stmt = select(ValidationIssue)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ValidationIssue)

        if organization_id is not None:
            stmt = stmt.where(ValidationIssue.organization_id == organization_id)
            count_stmt = count_stmt.where(ValidationIssue.organization_id == organization_id)

        if load_id is not None:
            stmt = stmt.where(ValidationIssue.load_id == load_id)
            count_stmt = count_stmt.where(ValidationIssue.load_id == load_id)

        if document_id is not None:
            stmt = stmt.where(ValidationIssue.document_id == document_id)
            count_stmt = count_stmt.where(ValidationIssue.document_id == document_id)

        if severity is not None:
            stmt = stmt.where(ValidationIssue.severity == severity)
            count_stmt = count_stmt.where(ValidationIssue.severity == severity)

        if is_resolved is not None:
            stmt = stmt.where(ValidationIssue.is_resolved == is_resolved)
            count_stmt = count_stmt.where(ValidationIssue.is_resolved == is_resolved)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(ValidationIssue.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def count_blocking_unresolved_for_load(self, load_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ValidationIssue)
            .where(
                ValidationIssue.load_id == load_id,
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