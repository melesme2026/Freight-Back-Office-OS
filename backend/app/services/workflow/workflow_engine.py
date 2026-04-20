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
from app.services.loads.packet_readiness import calculate_packet_readiness
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

        self._assert_transition_preconditions(
            load=load,
            current_status=current_status,
            target_status=target_status,
        )

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

        if normalized_action == "submit_to_broker":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.SUBMITTED_TO_BROKER,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Submitted to broker for payment.",
            )

        if normalized_action == "submit_to_factoring":
            result = self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.SUBMITTED_TO_FACTORING,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Submitted packet to factoring.",
            )
            self._update_operational_metadata(
                load_id=load_id,
                follow_up_required=True if follow_up_required is None else follow_up_required,
            )
            return result

        if normalized_action == "mark_packet_rejected":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.PACKET_REJECTED,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Packet rejected and requires corrections.",
            )

        if normalized_action == "mark_resubmission_needed":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.RESUBMISSION_NEEDED,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Resubmission required due to missing/invalid documents.",
            )

        if normalized_action == "mark_advance_paid":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.ADVANCE_PAID,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Factoring advance paid.",
            )

        if normalized_action == "mark_reserve_pending":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.RESERVE_PENDING,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Reserve amount is pending release.",
            )

        if normalized_action == "mark_fully_paid":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.FULLY_PAID,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Load marked fully paid.",
            )

        if normalized_action == "mark_short_paid":
            return self.transition_load(
                load_id=load_id,
                new_status=LoadStatus.SHORT_PAID,
                actor_staff_user_id=actor_staff_user_id,
                actor_type=actor_type,
                notes=normalized_notes or "Load marked short paid.",
            )

        return self.transition_load(
            load_id=load_id,
            new_status=LoadStatus.DISPUTED,
            actor_staff_user_id=actor_staff_user_id,
            actor_type=actor_type,
            notes=normalized_notes or "Load payment is in dispute.",
        )

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

        aliases: dict[str, LoadStatus] = {
            "new": LoadStatus.BOOKED,
            "needs_review": LoadStatus.DOCS_NEEDS_ATTENTION,
            "ready_to_submit": LoadStatus.INVOICE_READY,
            "waiting_on_broker": LoadStatus.SUBMITTED_TO_BROKER,
            "waiting_on_funding": LoadStatus.RESERVE_PENDING,
            "funded": LoadStatus.ADVANCE_PAID,
            "paid": LoadStatus.FULLY_PAID,
            "exception": LoadStatus.DOCS_NEEDS_ATTENTION,
        }
        if normalized in aliases:
            return aliases[normalized]

        for status in LoadStatus:
            if normalized == status.value.lower() or normalized == status.name.lower():
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
            "submit_to_broker",
            "submit_to_factoring",
            "mark_packet_rejected",
            "mark_resubmission_needed",
            "mark_advance_paid",
            "mark_reserve_pending",
            "mark_fully_paid",
            "mark_short_paid",
            "mark_disputed",
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
            LoadStatus.INVOICE_READY,
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.ADVANCE_PAID,
            LoadStatus.RESERVE_PENDING,
            LoadStatus.FULLY_PAID,
            LoadStatus.SHORT_PAID,
            LoadStatus.DISPUTED,
        }:
            blocking_issue_count = self.validation_repo.count_blocking_unresolved_for_load(load.id)
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

        if target_status in {LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING}:
            document_types = [
                document.document_type for document in (load.documents or []) if document.document_type
            ]
            readiness = calculate_packet_readiness(document_types=document_types)
            missing_submission_docs = readiness["missing_required_documents"]["submission"]
            if missing_submission_docs:
                raise ValidationError(
                    "Load cannot be submitted until required submission documents are present",
                    details={
                        "load_id": str(load.id),
                        "current_status": str(current_status),
                        "target_status": str(target_status),
                        "missing_documents": missing_submission_docs,
                        "readiness_state": readiness["readiness_state"],
                    },
                )

        if target_status in {LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING} and current_status not in {
            LoadStatus.INVOICE_READY,
            LoadStatus.RESUBMISSION_NEEDED,
        }:
            raise ValidationError(
                "Load can only be submitted from invoice-ready or resubmission-needed stages",
                details={
                    "load_id": str(load.id),
                    "current_status": str(current_status),
                    "target_status": str(target_status),
                },
            )

        if target_status in {LoadStatus.PACKET_REJECTED, LoadStatus.RESUBMISSION_NEEDED, LoadStatus.ADVANCE_PAID, LoadStatus.RESERVE_PENDING}:
            if not self._has_factoring_path(load=load, current_status=current_status):
                raise ValidationError(
                    "Factoring lifecycle updates require a factoring submission path",
                    details={
                        "load_id": str(load.id),
                        "current_status": str(current_status),
                        "target_status": str(target_status),
                    },
                )

        if target_status in {LoadStatus.FULLY_PAID, LoadStatus.SHORT_PAID, LoadStatus.DISPUTED} and load.submitted_at is None:
            raise ValidationError(
                "Payment/dispute states require prior broker/factoring submission",
                details={
                    "load_id": str(load.id),
                    "current_status": str(current_status),
                    "target_status": str(target_status),
                },
            )

    @staticmethod
    def _has_factoring_path(*, load: Load, current_status: LoadStatus) -> bool:
        if current_status in {
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.PACKET_REJECTED,
            LoadStatus.RESUBMISSION_NEEDED,
            LoadStatus.ADVANCE_PAID,
            LoadStatus.RESERVE_PENDING,
        }:
            return True

        return any(
            str(getattr(event, "new_status", "")).strip().lower() == LoadStatus.SUBMITTED_TO_FACTORING.value
            for event in (load.workflow_events or [])
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
