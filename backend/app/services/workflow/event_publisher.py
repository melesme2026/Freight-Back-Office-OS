from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.enums.load_status import LoadStatus
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
        old_status: str | LoadStatus | None = None,
        new_status: str | LoadStatus | None = None,
        event_payload: dict[str, Any] | list[Any] | None = None,
        actor_staff_user_id: str | None = None,
        actor_type: str | AuditActorType = AuditActorType.SYSTEM,
    ) -> WorkflowEvent:
        now = datetime.now(timezone.utc)
        normalized_event_type = self._require_text(event_type, field_name="event_type")
        normalized_actor_type = self._normalize_actor_type(actor_type)
        normalized_old_status = self._normalize_load_status(old_status, allow_none=True)
        normalized_new_status = self._normalize_load_status(new_status, allow_none=True)
        normalized_actor_staff_user_id = self._normalize_optional_uuid(actor_staff_user_id)

        event = WorkflowEvent(
            organization_id=organization_id,
            load_id=load_id,
            event_type=normalized_event_type,
            old_status=normalized_old_status,
            new_status=normalized_new_status,
            event_payload=event_payload,
            actor_staff_user_id=normalized_actor_staff_user_id,
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

    def _normalize_load_status(
        self,
        value: str | LoadStatus | None,
        *,
        allow_none: bool = False,
    ) -> LoadStatus | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                "status is required",
                details={"status": value},
            )

        if isinstance(value, LoadStatus):
            return value

        normalized = str(value).strip().lower()

        for status in LoadStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValidationError(
            "Invalid load status",
            details={"status": value},
        )

    def _normalize_optional_uuid(self, value: str | None) -> uuid.UUID | None:
        cleaned = self._clean_text(value)
        if cleaned is None:
            return None

        try:
            return uuid.UUID(cleaned)
        except ValueError as exc:
            raise ValidationError(
                "Invalid actor_staff_user_id",
                details={"actor_staff_user_id": value},
            ) from exc

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if cleaned is None:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned