from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load
from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository
from app.services.workflow.event_publisher import EventPublisher
from app.services.workflow.state_machine import LoadStateMachine
from app.services.workflow.transitions import LoadTransitionApplier


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)
        self.validation_repo = ValidationRepository(db)
        self.state_machine = LoadStateMachine()
        self.transition_applier = LoadTransitionApplier()
        self.event_publisher = EventPublisher(db)

    def get_load(self, load_id: str) -> Load:
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def transition_load(
        self,
        *,
        load_id: str,
        new_status: LoadStatus,
        actor_staff_user_id: str | None = None,
        actor_type: str | AuditActorType = AuditActorType.SYSTEM,
        notes: str | None = None,
    ) -> dict[str, Any]:
        load = self.get_load(load_id)

        current_status = self._normalize_load_status(load.status)
        target_status = self._normalize_load_status(new_status)
        normalized_actor_type = self._normalize_actor_type(actor_type)
        changed_at = datetime.now(timezone.utc)

        self.state_machine.assert_transition_allowed(
            current_status=current_status,
            new_status=target_status,
        )

        if target_status in {
            LoadStatus.VALIDATED,
            LoadStatus.READY_TO_SUBMIT,
            LoadStatus.SUBMITTED,
        }:
            blocking_issue_count = self.validation_repo.count_blocking_unresolved_for_load(
                load.id
            )
            if blocking_issue_count > 0:
                raise ValidationError(
                    "Load cannot transition while unresolved blocking validation issues exist",
                    details={
                        "load_id": str(load.id),
                        "current_status": str(current_status),
                        "target_status": str(target_status),
                        "blocking_issue_count": blocking_issue_count,
                    },
                )

        old_status = current_status
        updated_load = self.transition_applier.apply_status_change(
            load=load,
            new_status=target_status,
        )

        updated_load.last_reviewed_at = changed_at
        if actor_staff_user_id:
            updated_load.last_reviewed_by = actor_staff_user_id

        self.load_repo.update(updated_load)

        self.event_publisher.publish_load_event(
            organization_id=str(updated_load.organization_id),
            load_id=str(updated_load.id),
            event_type="status_changed",
            old_status=str(old_status),
            new_status=str(target_status),
            event_payload={"notes": notes} if notes else None,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=str(normalized_actor_type),
        )

        return {
            "id": str(updated_load.id),
            "old_status": old_status,
            "new_status": target_status,
            "changed_at": changed_at,
        }

    def _normalize_load_status(self, value: LoadStatus | str) -> LoadStatus:
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

    def _normalize_actor_type(self, value: AuditActorType | str) -> AuditActorType:
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