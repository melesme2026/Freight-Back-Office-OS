from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums.audit_actor_type import AuditActorType
from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load
from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository
from app.services.notifications.notification_service import NotificationService
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
        self.notification_service = NotificationService(db)

    def get_load(self, load_id: str) -> Load:
        load = self.load_repo.get_by_id(load_id, include_related=True)
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
        normalized_actor_staff_user_id = self._normalize_optional_uuid(actor_staff_user_id)
        normalized_notes = self._clean_text(notes)
        changed_at = datetime.now(timezone.utc)

        self.state_machine.assert_transition_allowed(
            current_status=current_status,
            new_status=target_status,
        )

        self._assert_transition_preconditions(load=load, current_status=current_status, target_status=target_status)

        old_status = current_status
        updated_load = self.transition_applier.apply_status_change(
            load=load,
            new_status=target_status,
        )

        updated_load.last_reviewed_at = changed_at
        if normalized_actor_staff_user_id is not None:
            updated_load.last_reviewed_by = normalized_actor_staff_user_id

        self.load_repo.update(updated_load)

        self.event_publisher.publish_load_event(
            organization_id=str(updated_load.organization_id),
            load_id=str(updated_load.id),
            event_type="status_changed",
            old_status=str(old_status),
            new_status=str(target_status),
            event_payload={"notes": normalized_notes} if normalized_notes else None,
            actor_staff_user_id=str(normalized_actor_staff_user_id)
            if normalized_actor_staff_user_id is not None
            else None,
            actor_type=str(normalized_actor_type),
        )
        self._create_load_status_notification(
            load=updated_load,
            old_status=old_status,
            new_status=target_status,
        )

        return {
            "id": str(updated_load.id),
            "old_status": old_status,
            "new_status": target_status,
            "changed_at": changed_at,
        }

    def apply_operational_action(
        self,
        *,
        load_id: str,
        action: str,
        actor_staff_user_id: str | None = None,
        actor_type: str | AuditActorType = AuditActorType.SYSTEM,
        notes: str | None = None,
        follow_up_required: bool | None = None,
    ) -> dict[str, Any]:
        normalized_action = self._normalize_action(action)
        normalized_notes = self._clean_text(notes)

        if normalized_action == "mark_sent_to_broker":
            result = self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.SUBMITTED_TO_BROKER,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Marked as sent to broker.",
            )
            self._publish_operational_event(
                load_id=load_id,
                event_type="broker_contacted",
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes,
            )
            self._update_operational_metadata(
                load_id=load_id,
                last_contacted=True,
                follow_up_required=True if follow_up_required is None else follow_up_required,
            )
            return result

        if normalized_action == "mark_waiting_on_broker":
            result = self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.WAITING_ON_BROKER,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Marked as waiting on broker.",
            )
            self._update_operational_metadata(
                load_id=load_id,
                follow_up_required=True if follow_up_required is None else follow_up_required,
            )
            return result

        if normalized_action == "mark_submitted_to_factoring":
            result = self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.SUBMITTED_TO_FACTORING,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Marked as submitted to factoring.",
            )
            self._publish_operational_event(
                load_id=load_id,
                event_type="broker_response_received",
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes,
            )
            self._publish_operational_event(
                load_id=load_id,
                event_type="submitted_to_factoring",
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes,
            )
            self._update_operational_metadata(
                load_id=load_id,
                follow_up_required=True if follow_up_required is None else follow_up_required,
            )
            return result

        result = self.transition_load(
            load_id=load_id,
            new_status=LoadStatus.FUNDED,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=actor_type,
            notes=normalized_notes or "Marked as funded.",
        )
        self._publish_operational_event(
            load_id=load_id,
            event_type="funding_confirmed",
            actor_staff_user_id=actor_staff_user_id,
            actor_type=actor_type,
            notes=normalized_notes,
        )
        self._update_operational_metadata(
            load_id=load_id,
            follow_up_required=False if follow_up_required is None else follow_up_required,
        )
        return result

    def _create_load_status_notification(
        self,
        *,
        load: Load,
        old_status: LoadStatus,
        new_status: LoadStatus,
    ) -> None:
        try:
            self.notification_service.create_notification(
                organization_id=str(load.organization_id),
                channel="manual",
                direction="outbound",
                message_type="load_status_changed",
                customer_account_id=str(load.customer_account_id),
                driver_id=str(load.driver_id),
                load_id=str(load.id),
                subject="Load status updated",
                body_text=(
                    f"Load {load.load_number or load.id} moved from "
                    f"{old_status.value} to {new_status.value}."
                ),
                status="queued",
            )
        except Exception:
            return

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

    @staticmethod
    def _normalize_action(value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {
            "mark_sent_to_broker",
            "mark_waiting_on_broker",
            "mark_submitted_to_factoring",
            "mark_funded",
        }
        if normalized not in allowed:
            raise ValidationError(
                "Invalid workflow action",
                details={"action": value, "allowed_actions": sorted(allowed)},
            )
        return normalized

    def _assert_transition_preconditions(
        self,
        *,
        load: Load,
        current_status: LoadStatus,
        target_status: LoadStatus,
    ) -> None:
        if target_status in {
            LoadStatus.READY_TO_SUBMIT,
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.WAITING_ON_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.WAITING_ON_FUNDING,
            LoadStatus.FUNDED,
            LoadStatus.PAID,
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

        if target_status in {
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.WAITING_ON_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.WAITING_ON_FUNDING,
            LoadStatus.FUNDED,
            LoadStatus.PAID,
        }:
            missing_docs: list[str] = []
            if not bool(load.has_ratecon):
                missing_docs.append("rate_confirmation")
            if not bool(load.has_bol):
                missing_docs.append("bill_of_lading")
            if not bool(load.has_invoice):
                missing_docs.append("invoice")
            if missing_docs:
                raise ValidationError(
                    "Load cannot transition to broker/factoring stages until all required documents are present",
                    details={
                        "load_id": str(load.id),
                        "current_status": str(current_status),
                        "target_status": str(target_status),
                        "missing_documents": missing_docs,
                    },
                )

    def _publish_operational_event(
        self,
        *,
        load_id: str,
        event_type: str,
        actor_staff_user_id: str | None,
        actor_type: str | AuditActorType,
        notes: str | None,
    ) -> None:
        load = self.get_load(load_id)
        self.event_publisher.publish_load_event(
            organization_id=str(load.organization_id),
            load_id=str(load.id),
            event_type=event_type,
            old_status=str(load.status),
            new_status=str(load.status),
            event_payload={"notes": notes} if notes else None,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=actor_type,
        )

    def _update_operational_metadata(
        self,
        *,
        load_id: str,
        last_contacted: bool = False,
        follow_up_required: bool | None = None,
    ) -> None:
        load = self.get_load(load_id)
        now = datetime.now(timezone.utc)
        if last_contacted:
            load.last_contacted_at = now
        if follow_up_required is not None:
            load.follow_up_required = bool(follow_up_required)
        load.updated_at = now
        self.load_repo.update(load)
