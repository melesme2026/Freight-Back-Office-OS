from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
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
        actor_id: str | None = None,
        actor_type: str = "system",
        changes_json: dict[str, Any] | list[Any] | None = None,
        metadata_json: dict[str, Any] | list[Any] | None = None,
    ) -> AuditLog:
        try:
            parsed_entity_id = uuid.UUID(str(entity_id))
        except ValueError as exc:
            raise ValidationError(
                "Invalid entity_id for audit log",
                details={"entity_id": entity_id},
            ) from exc

        parsed_actor_id: uuid.UUID | None = None
        if actor_id:
            try:
                parsed_actor_id = uuid.UUID(str(actor_id))
            except ValueError as exc:
                raise ValidationError(
                    "Invalid actor_id for audit log",
                    details={"actor_id": actor_id},
                ) from exc

        log = AuditLog(
            organization_id=organization_id,
            actor_type=actor_type,
            actor_id=parsed_actor_id,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
            action=action,
            changes_json=changes_json,
            metadata_json=metadata_json,
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
        parsed_entity_id: uuid.UUID | None = None
        if entity_id:
            try:
                parsed_entity_id = uuid.UUID(str(entity_id))
            except ValueError as exc:
                raise ValidationError(
                    "Invalid entity_id filter for audit logs",
                    details={"entity_id": entity_id},
                ) from exc

        return self.audit_repo.list(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
            action=action,
            page=page,
            page_size=page_size,
        )