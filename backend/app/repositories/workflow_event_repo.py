from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.workflow_event import WorkflowEvent


class WorkflowEventRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, workflow_event: WorkflowEvent) -> WorkflowEvent:
        self.db.add(workflow_event)
        self.db.flush()
        self.db.refresh(workflow_event)
        return workflow_event

    def get_by_id(self, event_id: uuid.UUID | str) -> WorkflowEvent | None:
        normalized_id = self._normalize_uuid(event_id, field_name="event_id")
        stmt = select(WorkflowEvent).where(WorkflowEvent.id == normalized_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        event_type: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[WorkflowEvent], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(WorkflowEvent)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(WorkflowEvent)

        if organization_id is not None:
            normalized_organization_id = self._normalize_uuid(
                organization_id,
                field_name="organization_id",
            )
            stmt = stmt.where(WorkflowEvent.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(
                WorkflowEvent.organization_id == normalized_organization_id
            )

        if load_id is not None:
            normalized_load_id = self._normalize_uuid(load_id, field_name="load_id")
            stmt = stmt.where(WorkflowEvent.load_id == normalized_load_id)
            count_stmt = count_stmt.where(WorkflowEvent.load_id == normalized_load_id)

        if event_type:
            stmt = stmt.where(WorkflowEvent.event_type == event_type)
            count_stmt = count_stmt.where(WorkflowEvent.event_type == event_type)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(WorkflowEvent.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, workflow_event: WorkflowEvent) -> WorkflowEvent:
        self.db.add(workflow_event)
        self.db.flush()
        self.db.refresh(workflow_event)
        return workflow_event

    def delete(self, workflow_event: WorkflowEvent) -> None:
        self.db.delete(workflow_event)
        self.db.flush()

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc