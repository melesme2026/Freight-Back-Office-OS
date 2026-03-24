from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.models.workflow_event import WorkflowEvent
from app.repositories.workflow_event_repo import WorkflowEventRepository


class EventPublisher:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workflow_event_repo = WorkflowEventRepository(db)

    def publish_load_event(
        self,
        *,
        organization_id: str,
        load_id: str,
        event_type: str,
        old_status: str | None = None,
        new_status: str | None = None,
        event_payload: dict[str, Any] | list[Any] | None = None,
        actor_staff_user_id: str | None = None,
        actor_type: str | AuditActorType = AuditActorType.SYSTEM,
    ) -> WorkflowEvent:
        now = datetime.now(timezone.utc)
        normalized_actor_type = self._normalize_actor_type(actor_type)

        event = WorkflowEvent(
            organization_id=organization_id,
            load_id=load_id,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            event_payload=event_payload,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=normalized_actor_type,
            created_at=now,
            updated_at=now,
        )
        return self.workflow_event_repo.create(event)

    def _normalize_actor_type(self, value: str | AuditActorType) -> AuditActorType:
        if isinstance(value, AuditActorType):
            return value

        normalized = str(value).strip().lower()

        for actor_type in AuditActorType:
            if normalized == actor_type.value.lower():
                return actor_type
            if normalized == actor_type.name.lower():
                return actor_type

        raise ValidationError(
            "Invalid actor_type",
            details={"actor_type": value},
        )