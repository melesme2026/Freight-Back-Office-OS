from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums.follow_up_task import FollowUpTaskPriority, FollowUpTaskStatus, FollowUpTaskType
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.follow_up_task import FollowUpTask
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.organization import Organization
from app.domain.models.submission_packet import SubmissionPacket

PAYMENT_TASK_TYPES = {
    FollowUpTaskType.PAYMENT_OVERDUE,
    FollowUpTaskType.RESERVE_FOLLOW_UP,
    FollowUpTaskType.PARTIAL_PAYMENT_FOLLOW_UP,
    FollowUpTaskType.SHORT_PAY_FOLLOW_UP,
    FollowUpTaskType.DISPUTE_FOLLOW_UP,
}


class FollowUpService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_followups_for_load(self, load_id: str, org_id: str) -> list[FollowUpTask]:
        load = self._get_load(load_id, org_id)
        now = datetime.now(timezone.utc)
        generated: list[FollowUpTask] = []

        packets = list(self.db.scalars(select(SubmissionPacket).where(SubmissionPacket.load_id == load.id, SubmissionPacket.organization_id == load.organization_id)).all())
        payment_record = self.db.scalar(select(LoadPaymentRecord).where(LoadPaymentRecord.load_id == load.id, LoadPaymentRecord.organization_id == load.organization_id))

        for packet in packets:
            sent_at = self._utc(getattr(packet, "sent_at", None))
            accepted_at = getattr(packet, "accepted_at", None)
            if sent_at and not accepted_at:
                due_at = sent_at + timedelta(days=7)
                if due_at <= now:
                    age_days = max((now - due_at).days, 0)
                    generated.append(
                        self.upsert_system_followup(
                            org_id=org_id,
                            load_id=str(load.id),
                            task_type=FollowUpTaskType.PACKET_FOLLOW_UP,
                            title="Follow up on submitted packet",
                            description="Packet was submitted but not yet accepted.",
                            recommended_action="Follow up with broker/factor on packet acceptance status.",
                            due_at=due_at,
                            priority=self.compute_followup_priority(base=FollowUpTaskPriority.NORMAL, days_past_due=age_days),
                            submission_packet_id=str(packet.id),
                        )
                    )

        if payment_record is not None:
            status = payment_record.payment_status
            submitted_at = self._utc(load.submitted_at or (packets[0].sent_at if packets and packets[0].sent_at else None))

            if status in {LoadPaymentStatus.PAID}:
                self._cancel_open_payment_tasks(load.id, load.organization_id)
            else:
                if submitted_at:
                    due_at = submitted_at + timedelta(days=30)
                    if due_at <= now and status not in {LoadPaymentStatus.NOT_SUBMITTED}:
                        generated.append(
                            self.upsert_system_followup(
                                org_id=org_id,
                                load_id=str(load.id),
                                task_type=FollowUpTaskType.PAYMENT_OVERDUE,
                                title="Payment overdue",
                                description="Payment is still pending beyond expected terms.",
                                recommended_action="Follow up with broker/factor about payment status.",
                                due_at=due_at,
                                priority=FollowUpTaskPriority.HIGH,
                                payment_record_id=str(payment_record.id),
                            )
                        )

                if status == LoadPaymentStatus.RESERVE_PENDING:
                    reserve_due = submitted_at or now
                    age_days = max((now - reserve_due).days, 0)
                    generated.append(
                        self.upsert_system_followup(
                            org_id=org_id,
                            load_id=str(load.id),
                            task_type=FollowUpTaskType.RESERVE_FOLLOW_UP,
                            title="Reserve payment pending",
                            description="Factoring reserve has not been released.",
                            recommended_action="Follow up on reserve payment status.",
                            due_at=reserve_due,
                            priority=self.compute_followup_priority(base=FollowUpTaskPriority.NORMAL, days_past_due=age_days),
                            payment_record_id=str(payment_record.id),
                        )
                    )

                if status == LoadPaymentStatus.PARTIALLY_PAID:
                    generated.append(
                        self.upsert_system_followup(
                            org_id=org_id,
                            load_id=str(load.id),
                            task_type=FollowUpTaskType.PARTIAL_PAYMENT_FOLLOW_UP,
                            title="Follow up on remaining balance",
                            description="Payment was received but there is still an outstanding balance.",
                            recommended_action="Follow up with broker/factor to collect remaining balance.",
                            due_at=now,
                            priority=FollowUpTaskPriority.NORMAL,
                            payment_record_id=str(payment_record.id),
                        )
                    )

                if status == LoadPaymentStatus.SHORT_PAID:
                    generated.append(
                        self.upsert_system_followup(
                            org_id=org_id,
                            load_id=str(load.id),
                            task_type=FollowUpTaskType.SHORT_PAY_FOLLOW_UP,
                            title="Resolve short-pay",
                            description="Payment was short-paid versus expected amount.",
                            recommended_action="Resolve short-pay with broker/factor and collect difference.",
                            due_at=now,
                            priority=FollowUpTaskPriority.URGENT,
                            payment_record_id=str(payment_record.id),
                        )
                    )

                if status == LoadPaymentStatus.DISPUTED:
                    generated.append(
                        self.upsert_system_followup(
                            org_id=org_id,
                            load_id=str(load.id),
                            task_type=FollowUpTaskType.DISPUTE_FOLLOW_UP,
                            title="Resolve payment dispute",
                            description="Payment is currently disputed.",
                            recommended_action="Follow up to resolve dispute and confirm next action.",
                            due_at=now,
                            priority=FollowUpTaskPriority.URGENT,
                            payment_record_id=str(payment_record.id),
                        )
                    )

        self.db.flush()
        return generated

    def generate_followups_for_org(self, org_id: str) -> dict[str, int]:
        org_uuid = uuid.UUID(str(org_id))
        loads = list(self.db.scalars(select(Load).where(Load.organization_id == org_uuid)).all())
        created_or_updated = 0
        for load in loads:
            try:
                created_or_updated += len(self.generate_followups_for_load(str(load.id), str(org_uuid)))
            except Exception:
                continue
        return {"loads_processed": len(loads), "tasks_created_or_updated": created_or_updated}

    def list_followups(self, org_id: str, filters: dict[str, Any]) -> list[FollowUpTask]:
        stmt = select(FollowUpTask).where(FollowUpTask.organization_id == uuid.UUID(str(org_id)))
        if filters.get("status"):
            stmt = stmt.where(FollowUpTask.status == FollowUpTaskStatus(str(filters["status"])))
        if filters.get("priority"):
            stmt = stmt.where(FollowUpTask.priority == FollowUpTaskPriority(str(filters["priority"])))
        if filters.get("task_type"):
            stmt = stmt.where(FollowUpTask.task_type == FollowUpTaskType(str(filters["task_type"])))
        if filters.get("due_before"):
            stmt = stmt.where(FollowUpTask.due_at <= filters["due_before"])
        if filters.get("load_id"):
            stmt = stmt.where(FollowUpTask.load_id == uuid.UUID(str(filters["load_id"])))
        if filters.get("assigned_to_staff_user_id"):
            stmt = stmt.where(FollowUpTask.assigned_to_staff_user_id == uuid.UUID(str(filters["assigned_to_staff_user_id"])))
        return list(self.db.scalars(stmt.order_by(FollowUpTask.due_at.asc())).all())

    def complete_followup(self, task_id: str, org_id: str, actor: str | None) -> FollowUpTask:
        task = self._get_task(task_id, org_id)
        task.status = FollowUpTaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        return task

    def snooze_followup(self, task_id: str, org_id: str, until: datetime, actor: str | None) -> FollowUpTask:
        task = self._get_task(task_id, org_id)
        if until <= datetime.now(timezone.utc):
            raise ValidationError("Snooze time must be in the future")
        task.status = FollowUpTaskStatus.SNOOZED
        task.snoozed_until = until
        return task

    def cancel_followup(self, task_id: str, org_id: str, actor: str | None) -> FollowUpTask:
        task = self._get_task(task_id, org_id)
        task.status = FollowUpTaskStatus.CANCELED
        return task

    def upsert_system_followup(
        self,
        *,
        org_id: str,
        load_id: str,
        task_type: FollowUpTaskType,
        title: str,
        description: str,
        recommended_action: str,
        due_at: datetime,
        priority: FollowUpTaskPriority,
        submission_packet_id: str | None = None,
        payment_record_id: str | None = None,
    ) -> FollowUpTask:
        clause = [
            FollowUpTask.organization_id == uuid.UUID(str(org_id)),
            FollowUpTask.load_id == uuid.UUID(str(load_id)),
            FollowUpTask.task_type == task_type,
            FollowUpTask.created_by_system.is_(True),
            FollowUpTask.status.in_([FollowUpTaskStatus.OPEN, FollowUpTaskStatus.SNOOZED]),
            FollowUpTask.submission_packet_id == (uuid.UUID(submission_packet_id) if submission_packet_id else None),
            FollowUpTask.payment_record_id == (uuid.UUID(payment_record_id) if payment_record_id else None),
        ]
        existing = self.db.scalar(select(FollowUpTask).where(*clause))
        if existing:
            existing.title = title
            existing.description = description
            existing.recommended_action = recommended_action
            existing.due_at = due_at
            existing.priority = priority
            return existing

        task = FollowUpTask(
            organization_id=uuid.UUID(str(org_id)),
            load_id=uuid.UUID(str(load_id)),
            submission_packet_id=uuid.UUID(submission_packet_id) if submission_packet_id else None,
            payment_record_id=uuid.UUID(payment_record_id) if payment_record_id else None,
            task_type=task_type,
            status=FollowUpTaskStatus.OPEN,
            priority=priority,
            title=title,
            description=description,
            recommended_action=recommended_action,
            due_at=due_at,
            created_by_system=True,
        )
        self.db.add(task)
        return task

    def compute_followup_priority(self, *, base: FollowUpTaskPriority, days_past_due: int) -> FollowUpTaskPriority:
        if base == FollowUpTaskPriority.URGENT:
            return base
        if days_past_due >= 14:
            return FollowUpTaskPriority.HIGH
        return base

    def _cancel_open_payment_tasks(self, load_id: uuid.UUID, org_id: uuid.UUID) -> None:
        tasks = list(
            self.db.scalars(
                select(FollowUpTask).where(
                    FollowUpTask.organization_id == org_id,
                    FollowUpTask.load_id == load_id,
                    FollowUpTask.task_type.in_(PAYMENT_TASK_TYPES),
                    FollowUpTask.status.in_([FollowUpTaskStatus.OPEN, FollowUpTaskStatus.SNOOZED]),
                    FollowUpTask.created_by_system.is_(True),
                )
            ).all()
        )
        for task in tasks:
            task.status = FollowUpTaskStatus.CANCELED

    def _get_load(self, load_id: str, org_id: str) -> Load:
        load = self.db.get(Load, uuid.UUID(str(load_id)))
        if load is None or str(load.organization_id) != str(org_id):
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def _get_task(self, task_id: str, org_id: str) -> FollowUpTask:
        task = self.db.get(FollowUpTask, uuid.UUID(str(task_id)))
        if task is None or str(task.organization_id) != str(org_id):
            raise NotFoundError("Follow-up task not found", details={"task_id": task_id})
        return task

    def _utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
