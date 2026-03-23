from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models.audit_log import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_repo = AuditRepository(db)

    def log_event(
        self,
        *,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_staff_user_id: str | None = None,
        actor_type: str = "system",
        metadata_json: dict[str, Any] | list[Any] | None = None,
    ) -> AuditLog:
        log = AuditLog(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=actor_type,
            metadata_json=metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.audit_repo.create(log)

    def list_audit_logs(
        self,
        *,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[AuditLog], int]:
        return self.audit_repo.list(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            page=page,
            page_size=page_size,
        )