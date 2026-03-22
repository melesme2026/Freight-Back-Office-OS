from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.workflow_event import WorkflowEvent


class WorkflowEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, workflow_event: WorkflowEvent) -> WorkflowEvent:
        self.db.add(workflow_event)
        self.db.flush()
        self.db.refresh(workflow_event)
        return workflow_event

    def get_by_id(self, event_id: uuid.UUID) -> WorkflowEvent | None:
        stmt = select(WorkflowEvent).where(WorkflowEvent.id == event_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[WorkflowEvent], int]:
        stmt = select(WorkflowEvent)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(WorkflowEvent)

        if organization_id is not None:
            stmt = stmt.where(WorkflowEvent.organization_id == organization_id)
            count_stmt = count_stmt.where(WorkflowEvent.organization_id == organization_id)

        if load_id is not None:
            stmt = stmt.where(WorkflowEvent.load_id == load_id)
            count_stmt = count_stmt.where(WorkflowEvent.load_id == load_id)

        if event_type:
            stmt = stmt.where(WorkflowEvent.event_type == event_type)
            count_stmt = count_stmt.where(WorkflowEvent.event_type == event_type)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(WorkflowEvent.created_at.desc())
            .offset(offset)
            .limit(page_size)
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