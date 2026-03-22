from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, audit_log: AuditLog) -> AuditLog:
        self.db.add(audit_log)
        self.db.flush()
        self.db.refresh(audit_log)
        return audit_log

    def get_by_id(self, audit_log_id: uuid.UUID) -> AuditLog | None:
        stmt = select(AuditLog).where(AuditLog.id == audit_log_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(AuditLog)

        if organization_id is not None:
            stmt = stmt.where(AuditLog.organization_id == organization_id)
            count_stmt = count_stmt.where(AuditLog.organization_id == organization_id)

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
            count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)

        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
            count_stmt = count_stmt.where(AuditLog.entity_id == entity_id)

        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, audit_log: AuditLog) -> AuditLog:
        self.db.add(audit_log)
        self.db.flush()
        self.db.refresh(audit_log)
        return audit_log

    def delete(self, audit_log: AuditLog) -> None:
        self.db.delete(audit_log)
        self.db.flush()