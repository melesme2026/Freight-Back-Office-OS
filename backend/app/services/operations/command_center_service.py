from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.cache import CacheKey, operational_cache
from app.domain.enums.document_type import DocumentType
from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.follow_up_task import FollowUpTaskStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.audit_log import AuditLog
from app.domain.models.driver import Driver
from app.domain.models.follow_up_task import FollowUpTask
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.submission_packet import SubmissionPacket
from app.domain.models.validation_issue import ValidationIssue
from app.services.loads.packet_readiness import calculate_load_packet_readiness
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

ZERO = Decimal("0.00")
COMMAND_CENTER_LOAD_LIMIT = 200
COMMAND_CENTER_PAYMENT_LIMIT = 200
COMMAND_CENTER_ACTIVITY_LIMIT = 12
COMMAND_CENTER_CACHE_TTL_SECONDS = 20

ACTIVE_LOAD_STATUSES = {
    LoadStatus.BOOKED,
    LoadStatus.IN_TRANSIT,
    LoadStatus.DELIVERED,
    LoadStatus.DOCS_RECEIVED,
    LoadStatus.DOCS_NEEDS_ATTENTION,
    LoadStatus.INVOICE_READY,
    LoadStatus.SUBMITTED_TO_BROKER,
    LoadStatus.SUBMITTED_TO_FACTORING,
    LoadStatus.PACKET_REJECTED,
    LoadStatus.RESUBMISSION_NEEDED,
    LoadStatus.ADVANCE_PAID,
    LoadStatus.RESERVE_PENDING,
    LoadStatus.SHORT_PAID,
    LoadStatus.DISPUTED,
}

UNPAID_PAYMENT_STATUSES = {
    LoadPaymentStatus.NOT_SUBMITTED,
    LoadPaymentStatus.SUBMITTED,
    LoadPaymentStatus.AWAITING_PAYMENT,
    LoadPaymentStatus.PARTIALLY_PAID,
    LoadPaymentStatus.ADVANCE_PAID,
    LoadPaymentStatus.RESERVE_PENDING,
    LoadPaymentStatus.SHORT_PAID,
    LoadPaymentStatus.DISPUTED,
}

BLOCKED_PACKET_STATUSES = {"blocked", "failed", "rejected", "needs_attention"}
PENDING_PACKET_STATUSES = {"draft", "ready", "queued"}


class DispatcherCommandCenterService:
    """Deterministic operational command center for dispatcher workflows.

    The service intentionally works from existing load, packet, payment, validation,
    and audit state. It does not score loads with AI, does not ingest telematics, and
    limits result sets so the dashboard remains responsive for daily operations.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_command_center(self, *, org_id: str) -> dict[str, Any]:
        cache_key = CacheKey(
            namespace="command_center",
            organization_id=org_id,
            parts=(self._cache_fingerprint(org_id),),
        )
        cached = operational_cache.get(cache_key)
        if cached is not None:
            return deepcopy(cached)

        today = datetime.now(timezone.utc).date()
        loads = self._load_recent_operational_loads(org_id=org_id)
        payments = self._load_payment_records(org_id=org_id)
        packets = self._load_packets(org_id=org_id)
        unresolved_blockers = self._load_unresolved_blockers(org_id=org_id)
        open_follow_ups = self._load_open_follow_ups(org_id=org_id)
        active_drivers = self._load_active_drivers(org_id=org_id)

        packet_by_load = self._group_packets_by_load(packets)
        blockers_by_load = self._group_blockers_by_load(unresolved_blockers)

        missing_docs = [
            self._missing_doc_item(
                load, packet_by_load.get(str(load.id), []), blockers_by_load.get(str(load.id), [])
            )
            for load in loads
        ]
        missing_docs = [
            item
            for item in missing_docs
            if item["missing_required_documents"] or item["blocked_from_packet_send"]
        ]
        missing_docs.sort(
            key=lambda item: (-int(item["priority_score"]), item["load_number"] or "")
        )

        collections = [
            self._collection_item(record, today=today)
            for record in payments
            if self._outstanding(record) > ZERO and record.payment_status in UNPAID_PAYMENT_STATUSES
        ]
        collections.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                -int(item["age_days"]),
                item["load_number"] or "",
            )
        )

        alerts = self._build_alerts(
            loads=loads,
            payments=payments,
            packet_by_load=packet_by_load,
            blockers_by_load=blockers_by_load,
            missing_doc_items=missing_docs,
            today=today,
        )
        tasks = self._build_tasks(
            missing_doc_items=missing_docs, collection_items=collections, alerts=alerts
        )
        broker_insights = self._broker_behavior_insights(payments, today=today)
        operational_intelligence = self._build_operational_intelligence(
            loads=loads,
            alerts=alerts,
            tasks=tasks,
            unresolved_blockers=unresolved_blockers,
            open_follow_ups=open_follow_ups,
            active_drivers=active_drivers,
            today=today,
        )
        ai_assistant = self._build_ai_operations_assistant(
            loads=loads,
            payments=payments,
            packets=packets,
            missing_docs=missing_docs,
            collections=collections,
            broker_insights=broker_insights,
            tasks=tasks,
            today=today,
        )

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kpis": self._build_kpis(
                org_id=org_id,
                loads=loads,
                payments=payments,
                packets=packets,
                unresolved_blockers=unresolved_blockers,
                open_follow_ups=open_follow_ups,
                active_drivers=active_drivers,
                today=today,
            ),
            "alerts": alerts[:25],
            "missing_docs": {
                "summary": self._missing_doc_summary(missing_docs),
                "items": missing_docs[:25],
            },
            "collections": {
                "summary": self._collections_summary(collections),
                "items": collections[:15],
            },
            "tasks": {
                "summary": self._task_summary(tasks),
                "items": tasks[:30],
            },
            "operational_intelligence": operational_intelligence,
            "ai_operations_assistant": ai_assistant,
            "broker_behavior": {
                "summary": self._broker_behavior_summary(broker_insights),
                "items": broker_insights[:10],
            },
            "priority_cards": self._priority_cards(
                alerts=alerts, missing_docs=missing_docs, collections=collections
            ),
            "recent_activity": self._recent_activity(org_id=org_id),
            "meta": {
                "load_limit": COMMAND_CENTER_LOAD_LIMIT,
                "payment_limit": COMMAND_CENTER_PAYMENT_LIMIT,
                "cache_ttl_seconds": COMMAND_CENTER_CACHE_TTL_SECONDS,
                "cache_scope": "organization_scoped",
                "logic": (
                    "Deterministic operational prioritization based on missing required documents, "
                    "packet blockers, unpaid aging, factoring reserve state, "
                    "reconciliation status, follow-up urgency, driver profile gaps, "
                    "broker payment behavior, and unresolved validation blockers."
                ),
                "ai_assistant_logic": (
                    "Rules-only assistant: summarizes current operational records, "
                    "ranks collections "
                    "by explicit aging/balance/status factors, and includes every "
                    "contributing factor "
                    "in each recommendation. No autonomous actions, probabilities, or hidden LLM "
                    "scoring are used."
                ),
                "not_implemented": [
                    "live GPS tracking",
                    "telematics ingestion",
                    "AI dispatch optimization",
                    "autonomous collections outreach",
                    "LLM-generated financial predictions",
                    "websocket streaming",
                ],
            },
        }
        operational_cache.set(
            cache_key, deepcopy(payload), ttl_seconds=COMMAND_CENTER_CACHE_TTL_SECONDS
        )
        return payload

    def _cache_fingerprint(
        self, org_id: str
    ) -> tuple[int, object, int, object, int, object, int, object, int, object, int, object]:
        load_count, load_newest = self.db.execute(
            select(func.count(Load.id), func.max(Load.updated_at)).where(
                Load.organization_id == org_id
            )
        ).one()
        payment_count, payment_newest = self.db.execute(
            select(func.count(LoadPaymentRecord.id), func.max(LoadPaymentRecord.updated_at)).where(
                LoadPaymentRecord.organization_id == org_id
            )
        ).one()
        blocker_count, blocker_newest = self.db.execute(
            select(func.count(ValidationIssue.id), func.max(ValidationIssue.updated_at)).where(
                ValidationIssue.organization_id == org_id
            )
        ).one()
        document_count, document_newest = self.db.execute(
            select(func.count(LoadDocument.id), func.max(LoadDocument.updated_at)).where(
                LoadDocument.organization_id == org_id
            )
        ).one()
        follow_up_count, follow_up_newest = self.db.execute(
            select(func.count(FollowUpTask.id), func.max(FollowUpTask.updated_at)).where(
                FollowUpTask.organization_id == org_id
            )
        ).one()
        driver_count, driver_newest = self.db.execute(
            select(func.count(Driver.id), func.max(Driver.updated_at)).where(
                Driver.organization_id == org_id
            )
        ).one()
        return (
            int(load_count or 0),
            load_newest,
            int(payment_count or 0),
            payment_newest,
            int(blocker_count or 0),
            blocker_newest,
            int(document_count or 0),
            document_newest,
            int(follow_up_count or 0),
            follow_up_newest,
            int(driver_count or 0),
            driver_newest,
        )

    def _load_recent_operational_loads(self, *, org_id: str) -> list[Load]:
        stmt = (
            select(Load)
            .where(Load.organization_id == org_id, Load.status.in_(ACTIVE_LOAD_STATUSES))
            .options(
                selectinload(Load.driver),
                selectinload(Load.broker),
                selectinload(Load.documents),
                selectinload(Load.validation_issues),
            )
            .order_by(Load.updated_at.desc(), Load.created_at.desc())
            .limit(COMMAND_CENTER_LOAD_LIMIT)
        )
        return list(self.db.scalars(stmt).unique().all())

    def _load_payment_records(self, *, org_id: str) -> list[LoadPaymentRecord]:
        stmt = (
            select(LoadPaymentRecord)
            .where(LoadPaymentRecord.organization_id == org_id)
            .options(
                selectinload(LoadPaymentRecord.load).selectinload(Load.driver),
                selectinload(LoadPaymentRecord.load).selectinload(Load.broker),
                selectinload(LoadPaymentRecord.load).selectinload(Load.documents),
            )
            .order_by(LoadPaymentRecord.updated_at.desc(), LoadPaymentRecord.created_at.desc())
            .limit(COMMAND_CENTER_PAYMENT_LIMIT)
        )
        return list(self.db.scalars(stmt).unique().all())

    def _load_packets(self, *, org_id: str) -> list[SubmissionPacket]:
        stmt = (
            select(SubmissionPacket)
            .where(SubmissionPacket.organization_id == org_id)
            .order_by(SubmissionPacket.updated_at.desc(), SubmissionPacket.created_at.desc())
            .limit(COMMAND_CENTER_LOAD_LIMIT)
        )
        return list(self.db.scalars(stmt).all())

    def _load_unresolved_blockers(self, *, org_id: str) -> list[ValidationIssue]:
        stmt = (
            select(ValidationIssue)
            .where(
                ValidationIssue.organization_id == org_id,
                ValidationIssue.is_resolved.is_(False),
                ValidationIssue.is_blocking.is_(True),
            )
            .order_by(ValidationIssue.created_at.desc())
            .limit(COMMAND_CENTER_LOAD_LIMIT)
        )
        return list(self.db.scalars(stmt).all())

    def _load_open_follow_ups(self, *, org_id: str) -> list[FollowUpTask]:
        stmt = (
            select(FollowUpTask)
            .where(
                FollowUpTask.organization_id == org_id,
                FollowUpTask.status.in_([FollowUpTaskStatus.OPEN, FollowUpTaskStatus.SNOOZED]),
            )
            .options(selectinload(FollowUpTask.load))
            .order_by(FollowUpTask.due_at.asc(), FollowUpTask.created_at.asc())
            .limit(COMMAND_CENTER_LOAD_LIMIT)
        )
        return list(self.db.scalars(stmt).unique().all())

    def _load_active_drivers(self, *, org_id: str) -> list[Driver]:
        stmt = (
            select(Driver)
            .where(Driver.organization_id == org_id, Driver.is_active.is_(True))
            .options(selectinload(Driver.loads))
            .order_by(Driver.full_name.asc())
            .limit(COMMAND_CENTER_LOAD_LIMIT)
        )
        return list(self.db.scalars(stmt).unique().all())

    def _build_kpis(
        self,
        *,
        org_id: str,
        loads: list[Load],
        payments: list[LoadPaymentRecord],
        packets: list[SubmissionPacket],
        unresolved_blockers: list[ValidationIssue],
        open_follow_ups: list[FollowUpTask],
        active_drivers: list[Driver],
        today: date,
    ) -> dict[str, Any]:
        active_loads = (
            self.db.scalar(
                select(func.count())
                .select_from(Load)
                .where(Load.organization_id == org_id, Load.status.in_(ACTIVE_LOAD_STATUSES))
            )
            or 0
        )
        unpaid_total = sum(
            (
                self._outstanding(record)
                for record in payments
                if record.payment_status in UNPAID_PAYMENT_STATUSES
            ),
            ZERO,
        )
        reserve_pending_total = sum((self._reserve_pending(record) for record in payments), ZERO)
        overdue = [
            record
            for record in payments
            if self._outstanding(record) > ZERO and self._age_days(record, today=today) > 30
        ]
        readiness_by_load = {str(load.id): calculate_load_packet_readiness(load=load, db=self.db) for load in loads}
        stalled_loads = self._stalled_load_items(loads, today=today)
        follow_up_summary = self._follow_up_summary(open_follow_ups)
        return {
            "active_loads": int(active_loads),
            "loads_missing_docs": sum(1 for readiness in readiness_by_load.values() if readiness["missing_required_documents"]["submission"]),
            "loads_ready_for_invoice": sum(1 for readiness in readiness_by_load.values() if readiness["ready_for_invoice"]),
            "loads_ready_to_submit": sum(1 for readiness in readiness_by_load.values() if readiness["ready_to_submit"]),
            "overdue_invoices": len(overdue),
            "urgent_collections": sum(
                1 for record in payments if self._collection_priority(record, today=today) >= 80
            ),
            "pending_packet_sends": sum(
                1 for packet in packets if self._packet_status(packet) in PENDING_PACKET_STATUSES
            ),
            "unresolved_packet_intelligence_blockers": len(unresolved_blockers),
            "unresolved_validation_issues": sum(1 for load in loads for issue in load.validation_issues if not issue.is_resolved),
            "stalled_loads": len(stalled_loads),
            "overdue_follow_ups": follow_up_summary["overdue"],
            "stale_follow_ups": follow_up_summary["stale"],
            "drivers_missing_profile_items": sum(1 for driver in active_drivers if self._driver_missing_items(driver)),
            "factoring_reserve_pending": sum(
                1
                for record in payments
                if self._reserve_pending(record) > ZERO
                or record.factoring_status == FactoringWorkflowStatus.RESERVE_PENDING
            ),
            "unpaid_total": self._money(unpaid_total),
            "factoring_reserve_pending_total": self._money(reserve_pending_total),
        }

    def _missing_doc_item(
        self, load: Load, packets: list[SubmissionPacket], blockers: list[ValidationIssue]
    ) -> dict[str, Any]:
        missing = self._missing_documents(load)
        packet_statuses = [self._packet_status(packet) for packet in packets]
        blocked = (
            bool(missing)
            or any(status in BLOCKED_PACKET_STATUSES for status in packet_statuses)
            or bool(blockers)
        )
        priority = self._missing_doc_priority(
            load=load, missing=missing, blocked=blocked, blocker_count=len(blockers)
        )
        return {
            "load_id": str(load.id),
            "load_number": load.load_number,
            "status": self._enum_value(load.status),
            "driver_name": load.driver.full_name if load.driver else None,
            "broker_name": load.broker.name if load.broker else load.broker_name_raw,
            "lane": self._lane_label(load),
            "delivery_date": load.delivery_date.isoformat() if load.delivery_date else None,
            "missing_required_documents": missing,
            "blocked_from_packet_send": blocked,
            "packet_statuses": packet_statuses,
            "unresolved_blockers": [issue.title for issue in blockers[:5]],
            "severity": self._severity(priority),
            "priority_score": priority,
            "reason": self._missing_doc_reason(
                load=load, missing=missing, blocked=blocked, blocker_count=len(blockers)
            ),
        }

    def _collection_item(self, record: LoadPaymentRecord, *, today: date) -> dict[str, Any]:
        priority = self._collection_priority(record, today=today)
        load = record.load
        return {
            "load_id": str(record.load_id),
            "load_number": load.load_number if load else None,
            "invoice_number": load.invoice_number if load else None,
            "broker_name": load.broker.name
            if load and load.broker
            else (load.broker_name_raw if load else None),
            "driver_name": load.driver.full_name if load and load.driver else None,
            "lane": self._lane_label(load),
            "payment_status": self._enum_value(record.payment_status),
            "factoring_status": self._enum_value(record.factoring_status),
            "reconciliation_status": self._enum_value(record.reconciliation_status),
            "expected_amount": self._money(record.expected_amount or ZERO),
            "amount_received": self._money(record.amount_received or ZERO),
            "outstanding_amount": self._money(self._outstanding(record)),
            "reserve_pending_amount": self._money(self._reserve_pending(record)),
            "age_days": self._age_days(record, today=today),
            "severity": self._severity(priority),
            "priority_score": priority,
            "reason": self._collection_reason(record, today=today),
        }

    def _build_alerts(
        self,
        *,
        loads: list[Load],
        payments: list[LoadPaymentRecord],
        packet_by_load: dict[str, list[SubmissionPacket]],
        blockers_by_load: dict[str, list[ValidationIssue]],
        missing_doc_items: list[dict[str, Any]],
        today: date,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for item in missing_doc_items:
            missing = set(item["missing_required_documents"])
            if DocumentType.PROOF_OF_DELIVERY.value in missing:
                alerts.append(
                    self._alert(
                        "missing_pod",
                        item["severity"],
                        item["priority_score"],
                        "Missing POD",
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/loads/" + item["load_id"],
                    )
                )
            if DocumentType.RATE_CONFIRMATION.value in missing:
                alerts.append(
                    self._alert(
                        "missing_rate_confirmation",
                        item["severity"],
                        item["priority_score"],
                        "Missing rate confirmation",
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/loads/" + item["load_id"],
                    )
                )
            if item["blocked_from_packet_send"] and (
                item["packet_statuses"] or item["unresolved_blockers"]
            ):
                alerts.append(
                    self._alert(
                        "blocked_packet_send",
                        "critical",
                        max(90, int(item["priority_score"])),
                        "Packet send blocked",
                        (
                            "Packet cannot be sent until required documents or blocking validation "
                            "issues are resolved."
                        ),
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/loads/" + item["load_id"],
                    )
                )

        for record in payments:
            priority = self._collection_priority(record, today=today)
            if self._outstanding(record) > ZERO and self._age_days(record, today=today) > 30:
                alerts.append(
                    self._alert(
                        "invoice_overdue",
                        self._severity(priority),
                        priority,
                        "Invoice overdue",
                        self._collection_reason(record, today=today),
                        str(record.load_id),
                        record.load.load_number if record.load else None,
                        "/dashboard/money",
                    )
                )
            if (
                record.reconciliation_status != FactoringReconciliationStatus.RECONCILED
                and record.amount_received
                and record.amount_received > ZERO
            ):
                alerts.append(
                    self._alert(
                        "failed_reconciliation",
                        "warning",
                        70,
                        "Reconciliation needs review",
                        "Payment money was recorded but reconciliation is not complete.",
                        str(record.load_id),
                        record.load.load_number if record.load else None,
                        "/dashboard/factoring",
                    )
                )
            if (
                self._reserve_pending(record) > ZERO
                or record.factoring_status == FactoringWorkflowStatus.RESERVE_PENDING
            ):
                alerts.append(
                    self._alert(
                        "factoring_issue",
                        "warning",
                        75,
                        "Factoring reserve pending",
                        "Factored load still has reserve dollars pending collection.",
                        str(record.load_id),
                        record.load.load_number if record.load else None,
                        "/dashboard/factoring",
                    )
                )

        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for load in loads:
            updated_at = self._as_aware(load.updated_at)
            if (
                load.status in {LoadStatus.BOOKED, LoadStatus.IN_TRANSIT, LoadStatus.DELIVERED}
                and updated_at < stale_cutoff
            ):
                alerts.append(
                    self._alert(
                        "stale_load_activity",
                        "info",
                        35,
                        "Stale load activity",
                        "No operational update has been recorded in more than seven days.",
                        str(load.id),
                        load.load_number,
                        "/dashboard/loads/" + str(load.id),
                    )
                )
            blockers = blockers_by_load.get(str(load.id), [])
            if blockers:
                alerts.append(
                    self._alert(
                        "packet_intelligence_blocker",
                        "critical",
                        90,
                        "Packet intelligence blocker",
                        f"{len(blockers)} unresolved blocking validation issue(s) require review.",
                        str(load.id),
                        load.load_number,
                        "/dashboard/review-queue",
                    )
                )

        alerts.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                item["title"],
                item.get("load_number") or "",
            )
        )
        return alerts

    def _build_tasks(
        self,
        *,
        missing_doc_items: list[dict[str, Any]],
        collection_items: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for item in missing_doc_items:
            for doc_type in item["missing_required_documents"]:
                title = (
                    "Upload missing POD"
                    if doc_type == DocumentType.PROOF_OF_DELIVERY.value
                    else f"Upload missing {doc_type.replace('_', ' ')}"
                )
                tasks.append(
                    self._task(
                        "missing_document",
                        item["severity"],
                        item["priority_score"],
                        title,
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/documents",
                    )
                )
            if item["blocked_from_packet_send"] and item["unresolved_blockers"]:
                tasks.append(
                    self._task(
                        "review_blocked_packet",
                        "critical",
                        max(90, int(item["priority_score"])),
                        "Review blocked packet",
                        "Resolve packet intelligence blockers before resending.",
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/review-queue",
                    )
                )
            elif not item["missing_required_documents"] and item["blocked_from_packet_send"]:
                tasks.append(
                    self._task(
                        "resend_packet",
                        item["severity"],
                        item["priority_score"],
                        "Resend packet",
                        "Packet status indicates retry or review is needed.",
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/loads/" + item["load_id"],
                    )
                )

        for item in collection_items[:15]:
            if int(item["age_days"]) > 30:
                tasks.append(
                    self._task(
                        "follow_up_overdue_invoice",
                        item["severity"],
                        item["priority_score"],
                        "Follow up overdue invoice",
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/money",
                    )
                )
            if (
                item["reconciliation_status"] != FactoringReconciliationStatus.RECONCILED.value
                and item["amount_received"] != "0.00"
            ):
                tasks.append(
                    self._task(
                        "reconcile_payment",
                        "warning",
                        70,
                        "Reconcile payment",
                        "Payment has been received but reconciliation remains open.",
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/factoring",
                    )
                )
            if item["reserve_pending_amount"] != "0.00":
                tasks.append(
                    self._task(
                        "review_factoring_reserve",
                        "warning",
                        75,
                        "Review factoring reserve",
                        "Reserve balance is still pending release.",
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/factoring",
                    )
                )

        for alert in alerts:
            if alert["type"] == "stale_load_activity":
                tasks.append(
                    self._task(
                        "review_load_activity",
                        "info",
                        35,
                        "Review stale load",
                        alert["description"],
                        alert["load_id"],
                        alert["load_number"],
                        alert["href"],
                    )
                )

        deduped: dict[str, dict[str, Any]] = {}
        for task in tasks:
            deduped.setdefault(f"{task['type']}:{task['load_id']}:{task['title']}", task)
        result = list(deduped.values())
        result.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                item["title"],
                item.get("load_number") or "",
            )
        )
        return result

    def _priority_cards(
        self,
        *,
        alerts: list[dict[str, Any]],
        missing_docs: list[dict[str, Any]],
        collections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        critical_alerts = [alert for alert in alerts if alert["severity"] == "critical"]
        blocked_packets = [item for item in missing_docs if item["blocked_from_packet_send"]]
        urgent_collections = [item for item in collections if int(item["priority_score"]) >= 80]
        return [
            {
                "key": "critical_alerts",
                "label": "Critical operational alerts",
                "count": len(critical_alerts),
                "severity": "critical",
                "next_action": "Work these first; they block collections or packet movement.",
            },
            {
                "key": "blocked_packets",
                "label": "Blocked packet sends",
                "count": len(blocked_packets),
                "severity": "critical" if blocked_packets else "info",
                "next_action": "Resolve required documents and validation blockers.",
            },
            {
                "key": "urgent_collections",
                "label": "Urgent collections",
                "count": len(urgent_collections),
                "severity": "critical" if urgent_collections else "info",
                "next_action": "Follow up oldest and highest-risk unpaid invoices.",
            },
            {
                "key": "missing_docs",
                "label": "Loads missing docs",
                "count": len(missing_docs),
                "severity": "warning" if missing_docs else "info",
                "next_action": "Upload PODs, invoices, and rate confirmations.",
            },
        ]

    def _build_operational_intelligence(
        self,
        *,
        loads: list[Load],
        alerts: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        unresolved_blockers: list[ValidationIssue],
        open_follow_ups: list[FollowUpTask],
        active_drivers: list[Driver],
        today: date,
    ) -> dict[str, Any]:
        readiness_items = [self._readiness_item(load) for load in loads]
        readiness_items.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                item.get("load_number") or "",
            )
        )
        follow_up_items = [self._follow_up_item(task) for task in open_follow_ups]
        follow_up_items.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                item["due_at"] or "",
                item.get("load_number") or "",
            )
        )
        stalled_items = self._stalled_load_items(loads, today=today)
        driver_items = self._driver_visibility_items(active_drivers)
        needs_attention = self._needs_attention_items(
            alerts=alerts, tasks=tasks, follow_ups=follow_up_items, stalled_loads=stalled_items
        )
        ready_to_invoice = [item for item in readiness_items if item["ready_for_invoice"]]
        ready_to_submit = [item for item in readiness_items if item["ready_to_submit"]]
        invoice_blocked = [item for item in readiness_items if item["missing_invoice_documents"]]
        packet_blocked = [item for item in readiness_items if item["missing_submission_documents"]]
        validation_aging = self._validation_issue_aging(unresolved_blockers, today=today)
        return {
            "summary": {
                "needs_attention_count": len(needs_attention),
                "ready_to_invoice_count": len(ready_to_invoice),
                "ready_to_submit_count": len(ready_to_submit),
                "invoice_blocked_count": len(invoice_blocked),
                "packet_blocked_count": len(packet_blocked),
                "overdue_follow_up_count": sum(1 for item in follow_up_items if item["urgency"] in {"overdue", "stale"}),
                "stalled_load_count": len(stalled_items),
                "driver_gap_count": len(driver_items),
                "unresolved_validation_issue_count": len(unresolved_blockers),
                "oldest_validation_issue_age_days": validation_aging["oldest_age_days"],
            },
            "needs_attention": needs_attention[:12],
            "readiness": {
                "summary": {
                    "ready_to_invoice": len(ready_to_invoice),
                    "ready_to_submit": len(ready_to_submit),
                    "blocked_invoice_readiness": len(invoice_blocked),
                    "blocked_packet_submission": len(packet_blocked),
                },
                "items": readiness_items[:20],
            },
            "follow_ups": {
                "summary": self._follow_up_summary(open_follow_ups),
                "items": follow_up_items[:15],
            },
            "stalled_loads": {
                "summary": {
                    "total": len(stalled_items),
                    "critical": sum(1 for item in stalled_items if item["severity"] == "critical"),
                    "warning": sum(1 for item in stalled_items if item["severity"] == "warning"),
                },
                "items": stalled_items[:15],
            },
            "driver_visibility": {
                "summary": {
                    "active_drivers": len(active_drivers),
                    "drivers_missing_profile_items": len(driver_items),
                    "drivers_with_active_loads": sum(
                        1 for driver in active_drivers if any(load.status in ACTIVE_LOAD_STATUSES for load in driver.loads)
                    ),
                },
                "items": driver_items[:12],
            },
            "validation_issues": validation_aging,
            "guardrails": {
                "uses_llm": False,
                "invoice_math_changed": False,
                "packet_readiness_rules_changed": False,
                "source": "existing operational records and packet readiness service",
            },
        }

    def _readiness_item(self, load: Load) -> dict[str, Any]:
        readiness = calculate_load_packet_readiness(load=load, db=self.db)
        missing_invoice = list(readiness["missing_required_documents"]["invoice"])
        missing_submission = list(readiness["missing_required_documents"]["submission"])
        priority = 0
        if missing_submission:
            priority += 35
        if missing_invoice and load.status in {LoadStatus.DELIVERED, LoadStatus.DOCS_RECEIVED, LoadStatus.INVOICE_READY}:
            priority += 25
        if readiness["ready_to_submit"] and load.status in {LoadStatus.DOCS_RECEIVED, LoadStatus.INVOICE_READY}:
            priority += 30
        if load.follow_up_required:
            priority += 20
        priority = min(priority, 100)
        if readiness["ready_to_submit"]:
            action = "Submit packet or invoice through billing workflow."
        elif readiness["ready_for_invoice"]:
            action = "Create invoice, then collect remaining submission documents."
        else:
            action = "Collect required documents before invoice or packet movement."
        return {
            "load_id": str(load.id),
            "load_number": load.load_number,
            "status": self._enum_value(load.status),
            "driver_name": load.driver.full_name if load.driver else None,
            "broker_name": load.broker.name if load.broker else load.broker_name_raw,
            "lane": self._lane_label(load),
            "readiness_state": readiness["readiness_state"],
            "ready_for_invoice": bool(readiness["ready_for_invoice"]),
            "ready_to_submit": bool(readiness["ready_to_submit"]),
            "present_required_documents": readiness["present_required_documents"],
            "missing_invoice_documents": missing_invoice,
            "missing_submission_documents": missing_submission,
            "missing_recommended_documents": readiness["missing_recommended_documents"],
            "blockers": readiness["blockers"],
            "next_action": action,
            "severity": self._severity(priority),
            "priority_score": priority,
            "href": "/dashboard/loads/" + str(load.id),
        }

    def _follow_up_item(self, task: FollowUpTask) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        due_at = self._as_aware(task.due_at)
        age_days = max((now.date() - due_at.date()).days, 0)
        urgency = "upcoming"
        priority = 30
        if due_at.date() <= now.date():
            urgency = "due_today"
            priority = 55
        if due_at < now:
            urgency = "overdue"
            priority = 70
        if age_days >= 3:
            urgency = "stale"
            priority = 90
        priority_value = self._enum_value(task.priority)
        if priority_value == "urgent":
            priority = min(priority + 20, 100)
        elif priority_value == "high":
            priority = min(priority + 10, 100)
        load = task.load
        return {
            "id": str(task.id),
            "type": self._enum_value(task.task_type),
            "title": task.title,
            "description": task.description,
            "recommended_action": task.recommended_action,
            "status": self._enum_value(task.status),
            "urgency": urgency,
            "due_at": due_at.isoformat(),
            "age_days": age_days,
            "load_id": str(task.load_id),
            "load_number": load.load_number if load else None,
            "severity": self._severity(priority),
            "priority_score": priority,
            "href": "/dashboard/follow-ups",
        }

    def _follow_up_summary(self, tasks: list[FollowUpTask]) -> dict[str, int]:
        items = [self._follow_up_item(task) for task in tasks]
        return {
            "open": len(tasks),
            "due_today": sum(1 for item in items if item["urgency"] == "due_today"),
            "overdue": sum(1 for item in items if item["urgency"] == "overdue"),
            "stale": sum(1 for item in items if item["urgency"] == "stale"),
        }

    def _stalled_load_items(self, loads: list[Load], *, today: date) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for load in loads:
            updated_at = self._as_aware(load.updated_at)
            age_days = max((today - updated_at.date()).days, 0)
            threshold = 5 if load.status in {LoadStatus.DELIVERED, LoadStatus.DOCS_RECEIVED, LoadStatus.DOCS_NEEDS_ATTENTION} else 7
            if age_days < threshold:
                continue
            priority = min(35 + age_days * 5, 100)
            items.append(
                {
                    "load_id": str(load.id),
                    "load_number": load.load_number,
                    "status": self._enum_value(load.status),
                    "driver_name": load.driver.full_name if load.driver else None,
                    "lane": self._lane_label(load),
                    "age_days": age_days,
                    "reason": f"No operational update in {age_days} day(s).",
                    "next_action": "Review load status, documents, and follow-up ownership.",
                    "severity": self._severity(priority),
                    "priority_score": priority,
                    "href": "/dashboard/loads/" + str(load.id),
                }
            )
        items.sort(key=lambda item: (-int(item["priority_score"]), -int(item["age_days"])))
        return items

    def _driver_visibility_items(self, drivers: list[Driver]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for driver in drivers:
            missing = self._driver_missing_items(driver)
            if not missing:
                continue
            active_load_count = sum(1 for load in driver.loads if load.status in ACTIVE_LOAD_STATUSES)
            priority = 45 + min(active_load_count * 15, 30)
            items.append(
                {
                    "driver_id": str(driver.id),
                    "driver_name": driver.full_name,
                    "missing_items": missing,
                    "active_load_count": active_load_count,
                    "severity": self._severity(priority),
                    "priority_score": priority,
                    "next_action": "Complete driver contact/profile details before assigning more document work.",
                    "href": "/dashboard/drivers/" + str(driver.id),
                }
            )
        items.sort(key=lambda item: (-int(item["priority_score"]), item["driver_name"]))
        return items

    def _driver_missing_items(self, driver: Driver) -> list[str]:
        missing: list[str] = []
        if not (driver.email or "").strip():
            missing.append("email")
        if not (driver.phone or "").strip():
            missing.append("phone")
        if not driver.customer_account_id:
            missing.append("customer_account")
        return missing

    def _needs_attention_items(
        self,
        *,
        alerts: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        follow_ups: list[dict[str, Any]],
        stalled_loads: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for alert in alerts[:15]:
            items.append({**alert, "source": "alert", "next_action": alert["description"]})
        for task in tasks[:15]:
            items.append({**task, "source": "task", "next_action": task["description"]})
        for follow_up in follow_ups[:10]:
            if follow_up["urgency"] in {"overdue", "stale", "due_today"}:
                items.append({**follow_up, "source": "follow_up", "next_action": follow_up.get("recommended_action") or follow_up.get("description") or "Complete follow-up."})
        for stalled in stalled_loads[:10]:
            items.append({**stalled, "source": "stalled_load", "title": "Review stalled load", "description": stalled["reason"]})
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            deduped.setdefault(f"{item.get('source')}:{item.get('id') or item.get('load_id')}", item)
        result = list(deduped.values())
        result.sort(
            key=lambda item: (
                -int(item.get("priority_score", 0)),
                -self._severity_order(str(item.get("severity", "info"))),
                str(item.get("title") or ""),
            )
        )
        return result

    def _validation_issue_aging(
        self, unresolved_blockers: list[ValidationIssue], *, today: date
    ) -> dict[str, Any]:
        ages = [max((today - self._as_aware(issue.created_at).date()).days, 0) for issue in unresolved_blockers]
        severity_counts = Counter(self._enum_value(issue.severity) for issue in unresolved_blockers)
        return {
            "unresolved_blocking_count": len(unresolved_blockers),
            "oldest_age_days": max(ages) if ages else 0,
            "aging_over_3_days": sum(1 for age in ages if age > 3),
            "by_severity": dict(sorted(severity_counts.items())),
        }

    def _build_ai_operations_assistant(
        self,
        *,
        loads: list[Load],
        payments: list[LoadPaymentRecord],
        packets: list[SubmissionPacket],
        missing_docs: list[dict[str, Any]],
        collections: list[dict[str, Any]],
        broker_insights: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        today: date,
    ) -> dict[str, Any]:
        summaries = self._assistant_summaries(
            loads=loads,
            payments=payments,
            packets=packets,
            missing_docs=missing_docs,
            collections=collections,
            broker_insights=broker_insights,
            today=today,
        )
        invoice_risks = self._invoice_risk_items(payments, today=today)
        collection_priorities = self._collection_priorities(
            collections, broker_insights=broker_insights
        )
        recommendations = self._assistant_recommendations(
            missing_docs=missing_docs,
            invoice_risks=invoice_risks,
            collection_priorities=collection_priorities,
            broker_insights=broker_insights,
            tasks=tasks,
        )
        return {
            "summary": summaries,
            "invoice_risks": invoice_risks[:15],
            "broker_insights": broker_insights[:10],
            "collections_priorities": collection_priorities[:15],
            "recommendations": recommendations[:12],
            "explainability": {
                "mode": "deterministic_rules_only",
                "uses_llm": False,
                "autonomous_actions": False,
                "rules": [
                    (
                        "Invoice risk is derived from explicit aging, outstanding balance, "
                        "payment status, reconciliation status, reserve balance, and missing "
                        "packet documents."
                    ),
                    (
                        "Broker behavior is aggregated only from organization-scoped payment "
                        "records loaded for this command center response."
                    ),
                    (
                        "Collections priority is ordered by risk level, invoice age, outstanding "
                        "amount, and documented broker trend factors."
                    ),
                    (
                        "Recommendations are decision-support prompts only; users must choose "
                        "and perform any operational action."
                    ),
                ],
            },
        }

    def _assistant_summaries(
        self,
        *,
        loads: list[Load],
        payments: list[LoadPaymentRecord],
        packets: list[SubmissionPacket],
        missing_docs: list[dict[str, Any]],
        collections: list[dict[str, Any]],
        broker_insights: list[dict[str, Any]],
        today: date,
    ) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        missing_pod_count = sum(
            1
            for item in missing_docs
            if DocumentType.PROOF_OF_DELIVERY.value in item["missing_required_documents"]
        )
        if missing_pod_count:
            summaries.append(
                self._insight(
                    "dispatch_summary",
                    "warning",
                    f"{missing_pod_count} load(s) are blocked by missing POD.",
                    [f"{missing_pod_count} load(s) missing proof_of_delivery"],
                    "Upload or request POD before packet submission.",
                )
            )
        blocked_packet_count = sum(1 for item in missing_docs if item["blocked_from_packet_send"])
        if blocked_packet_count:
            summaries.append(
                self._insight(
                    "packet_blockers",
                    "critical",
                    f"{blocked_packet_count} load(s) have packet blockers requiring review.",
                    [f"{blocked_packet_count} blocked missing-doc or validation item(s)"],
                    "Resolve missing documents or validation blockers before resending packets.",
                )
            )
        ready_packets = sum(1 for packet in packets if self._packet_status(packet) == "ready")
        if ready_packets:
            summaries.append(
                self._insight(
                    "billing_ready",
                    "info",
                    f"{ready_packets} packet(s) are ready for billing submission.",
                    ["Submission packet status is ready"],
                    "Submit ready packets through the normal billing workflow.",
                )
            )
        overdue_45 = [item for item in collections if int(item["age_days"]) > 45]
        if overdue_45:
            total = sum((Decimal(item["outstanding_amount"]) for item in overdue_45), ZERO)
            summaries.append(
                self._insight(
                    "invoice_aging",
                    "critical",
                    (
                        f"{len(overdue_45)} invoice(s) are over 45 days overdue "
                        f"totaling {self._money(total)}."
                    ),
                    [
                        ">45 days since operational payment reference date",
                        f"Outstanding total {self._money(total)}",
                    ],
                    "Prioritize oldest high-balance invoices for collections follow-up.",
                )
            )
        reserve_total = sum((self._reserve_pending(record) for record in payments), ZERO)
        if reserve_total > ZERO:
            summaries.append(
                self._insight(
                    "reserve_pending",
                    "warning",
                    f"Factoring reserves pending total {self._money(reserve_total)}.",
                    ["reserve_amount minus reserve_paid_amount is greater than 0"],
                    "Review reserve release status with the factor or broker.",
                )
            )
        worsening = [item for item in broker_insights if item["trend"] == "worsening"]
        if worsening:
            broker = worsening[0]
            summaries.append(
                self._insight(
                    "broker_behavior",
                    "warning",
                    f"Broker {broker['broker_name']} has increasing aging exposure.",
                    broker["contributing_factors"],
                    broker["recommendation"],
                )
            )
        if not summaries:
            summaries.append(
                self._insight(
                    "operational_status",
                    "info",
                    "No high-risk operational blockers found in the current command center sample.",
                    [
                        (
                            f"Reviewed {len(loads)} active load(s) and {len(payments)} "
                            f"payment record(s) on {today.isoformat()}"
                        )
                    ],
                    "Continue normal dispatch, billing, and collections monitoring.",
                )
            )
        return summaries[:8]

    def _invoice_risk_items(
        self, payments: list[LoadPaymentRecord], *, today: date
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for record in payments:
            outstanding = self._outstanding(record)
            if outstanding <= ZERO or record.payment_status not in UNPAID_PAYMENT_STATUSES:
                continue
            missing: list[str] = []
            if record.load is not None:
                missing = self._missing_documents(record.load)
            risk = self._invoice_risk(record, missing_documents=missing, today=today)
            if risk["level"] == "low" and not missing:
                continue
            load = record.load
            items.append(
                {
                    "load_id": str(record.load_id),
                    "load_number": load.load_number if load else None,
                    "invoice_number": load.invoice_number if load else None,
                    "broker_name": load.broker.name
                    if load and load.broker
                    else (load.broker_name_raw if load else None),
                    "outstanding_amount": self._money(outstanding),
                    "age_days": self._age_days(record, today=today),
                    "risk_level": risk["level"],
                    "priority_score": risk["priority_score"],
                    "risk_reasons": risk["reasons"],
                    "contributing_factors": risk["factors"],
                    "recommended_action": risk["recommended_action"],
                    "payment_status": self._enum_value(record.payment_status),
                    "factoring_status": self._enum_value(record.factoring_status),
                    "reconciliation_status": self._enum_value(record.reconciliation_status),
                    "missing_required_documents": missing,
                }
            )
        items.sort(
            key=lambda item: (
                -self._risk_order(item["risk_level"]),
                -int(item["priority_score"]),
                -int(item["age_days"]),
                -Decimal(item["outstanding_amount"]),
            )
        )
        return items

    def _invoice_risk(
        self, record: LoadPaymentRecord, *, missing_documents: list[str], today: date
    ) -> dict[str, Any]:
        age = self._age_days(record, today=today)
        score = 10
        reasons: list[str] = []
        factors = [
            f"age_days={age}",
            f"outstanding_amount={self._money(self._outstanding(record))}",
            f"payment_status={self._enum_value(record.payment_status)}",
        ]
        if age > 60:
            score += 55
            reasons.append(
                "Invoice is more than 60 days from the operational payment reference date."
            )
        elif age > 45:
            score += 45
            reasons.append(
                "Invoice is more than 45 days from the operational payment reference date."
            )
        elif age > 30:
            score += 30
            reasons.append(
                "Invoice is more than 30 days from the operational payment reference date."
            )
        if self._outstanding(record) >= Decimal("5000"):
            score += 15
            reasons.append("Outstanding balance is at least $5,000.")
        if record.payment_status in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}:
            score += 25
            reasons.append(f"Payment status is {record.payment_status.value}.")
        if self._reserve_pending(record) > ZERO:
            score += 15
            reasons.append("Factoring reserve remains pending.")
            factors.append(f"reserve_pending_amount={self._money(self._reserve_pending(record))}")
        if (
            record.reconciliation_status != FactoringReconciliationStatus.RECONCILED
            and (record.amount_received or ZERO) > ZERO
        ):
            score += 15
            reasons.append("Payment has money received but reconciliation is still open.")
        if missing_documents:
            score += 20
            reasons.append("Billing packet is blocked by missing required document(s).")
            factors.append("missing_required_documents=" + ",".join(missing_documents))
        score = min(score, 100)
        level = (
            "critical"
            if score >= 80
            else "high"
            if score >= 65
            else "medium"
            if score >= 35
            else "low"
        )
        if not reasons:
            reasons.append(
                "Open invoice has unpaid balance but no elevated deterministic risk trigger."
            )
        action = (
            "Follow up overdue invoice and document response."
            if age > 30
            else "Monitor invoice and keep packet documentation current."
        )
        if missing_documents:
            action = "Resolve missing packet document(s) before collections escalation."
        if self._reserve_pending(record) > ZERO:
            action = (
                "Review reserve release status and reconcile expected payment."
                if age <= 30
                else action
            )
        return {
            "level": level,
            "priority_score": score,
            "reasons": reasons,
            "factors": factors,
            "recommended_action": action,
        }

    def _broker_behavior_insights(
        self, payments: list[LoadPaymentRecord], *, today: date
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for record in payments:
            load = record.load
            raw_broker_name = (
                load.broker_name_raw if load else "Unknown broker"
            ) or "Unknown broker"
            broker_id = str(load.broker_id) if load and load.broker_id else f"raw:{raw_broker_name}"
            broker_name = (
                load.broker.name
                if load and load.broker
                else ((load.broker_name_raw if load else None) or "Unknown broker")
            )
            row = grouped.setdefault(
                broker_id,
                {
                    "broker_id": broker_id,
                    "broker_name": broker_name,
                    "records": [],
                    "paid_days": [],
                },
            )
            row["records"].append(record)
            if record.paid_date:
                row["paid_days"].append(
                    max(
                        (
                            self._as_aware(record.paid_date).date()
                            - self._payment_reference_date(record)
                        ).days,
                        0,
                    )
                )
        insights: list[dict[str, Any]] = []
        for row in grouped.values():
            records = row["records"]
            unpaid = [
                record
                for record in records
                if self._outstanding(record) > ZERO
                and record.payment_status in UNPAID_PAYMENT_STATUSES
            ]
            overdue = [record for record in unpaid if self._age_days(record, today=today) > 30]
            severe = [
                record
                for record in unpaid
                if self._age_days(record, today=today) > 45
                or record.payment_status
                in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}
            ]
            unpaid_total = sum((self._outstanding(record) for record in unpaid), ZERO)
            overdue_total = sum((self._outstanding(record) for record in overdue), ZERO)
            dispute_count = sum(
                1
                for record in records
                if record.payment_status
                in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}
            )
            unreconciled_count = sum(
                1
                for record in records
                if record.reconciliation_status != FactoringReconciliationStatus.RECONCILED
            )
            reserve_total = sum((self._reserve_pending(record) for record in records), ZERO)
            paid_days = row["paid_days"]
            average_payment_days = round(sum(paid_days) / len(paid_days), 1) if paid_days else None
            current_aging = (
                round(
                    sum((self._age_days(record, today=today) for record in unpaid), 0)
                    / len(unpaid),
                    1,
                )
                if unpaid
                else 0
            )
            historical_average = (
                average_payment_days if average_payment_days is not None else current_aging
            )
            trend = (
                "worsening"
                if (current_aging >= historical_average + 10 and unpaid) or len(severe) >= 2
                else "stable"
            )
            if not unpaid and dispute_count == 0 and reserve_total == ZERO:
                continue
            factors = [
                f"records_reviewed={len(records)}",
                f"unpaid_invoices={len(unpaid)}",
                f"overdue_invoices={len(overdue)}",
                f"unpaid_total={self._money(unpaid_total)}",
            ]
            if average_payment_days is not None:
                factors.append(f"average_paid_cycle_days={average_payment_days}")
            if current_aging:
                factors.append(f"current_unpaid_average_age_days={current_aging}")
            if dispute_count:
                factors.append(f"dispute_or_short_paid_count={dispute_count}")
            if unreconciled_count:
                factors.append(f"unreconciled_count={unreconciled_count}")
            if reserve_total > ZERO:
                factors.append(f"reserve_pending_total={self._money(reserve_total)}")
            recommendation = (
                "Prioritize oldest/highest-balance invoices and verify packet acceptance."
            )
            if dispute_count:
                recommendation = (
                    "Review dispute or short-pay details before standard collections follow-up."
                )
            if reserve_total > ZERO:
                recommendation = "Follow up on reserve release and reconcile factor payment status."
            insights.append(
                {
                    "broker_id": row["broker_id"],
                    "broker_name": row["broker_name"],
                    "trend": trend,
                    "average_payment_days": average_payment_days,
                    "current_unpaid_average_age_days": current_aging,
                    "unpaid_invoice_count": len(unpaid),
                    "overdue_invoice_count": len(overdue),
                    "dispute_or_short_paid_count": dispute_count,
                    "unreconciled_count": unreconciled_count,
                    "unpaid_total": self._money(unpaid_total),
                    "overdue_total": self._money(overdue_total),
                    "reserve_pending_total": self._money(reserve_total),
                    "contributing_factors": factors,
                    "recommendation": recommendation,
                }
            )
        insights.sort(
            key=lambda item: (
                item["trend"] != "worsening",
                -int(item["overdue_invoice_count"]),
                -Decimal(item["unpaid_total"]),
                item["broker_name"],
            )
        )
        return insights

    def _collection_priorities(
        self, collections: list[dict[str, Any]], *, broker_insights: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        broker_by_name = {item["broker_name"]: item for item in broker_insights}
        priorities: list[dict[str, Any]] = []
        for item in collections:
            broker = broker_by_name.get(item.get("broker_name"))
            factors = [item["reason"], f"priority_score={item['priority_score']}"]
            if broker and broker["trend"] == "worsening":
                factors.append("broker_trend=worsening")
            action = (
                "Follow up overdue invoice and record the broker response."
                if int(item["age_days"]) > 30
                else "Monitor unpaid invoice and keep packet documentation ready."
            )
            if item["reserve_pending_amount"] != "0.00":
                action = "Follow up reserve release with the factor or broker."
            priorities.append(
                {
                    **item,
                    "collection_rank_reason": factors,
                    "broker_trend": broker["trend"] if broker else "not_enough_history",
                    "recommended_action": action,
                }
            )
        priorities.sort(
            key=lambda item: (
                -int(item["priority_score"]),
                -int(item["age_days"]),
                -Decimal(item["outstanding_amount"]),
                item.get("broker_name") or "",
            )
        )
        return priorities

    def _assistant_recommendations(
        self,
        *,
        missing_docs: list[dict[str, Any]],
        invoice_risks: list[dict[str, Any]],
        collection_priorities: list[dict[str, Any]],
        broker_insights: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        for item in missing_docs[:5]:
            missing = item["missing_required_documents"]
            if missing:
                action = (
                    "Upload missing POD"
                    if DocumentType.PROOF_OF_DELIVERY.value in missing
                    else "Upload missing packet document"
                )
                recommendations.append(
                    self._recommendation(
                        "missing_documents",
                        item["severity"],
                        action,
                        (
                            f"Load {item['load_number'] or item['load_id']} is blocked by "
                            "missing required document(s)."
                        ),
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/documents",
                        ["missing_required_documents=" + ",".join(missing)],
                    )
                )
            elif item["blocked_from_packet_send"]:
                recommendations.append(
                    self._recommendation(
                        "blocked_packet",
                        item["severity"],
                        "Review blocked packet",
                        (
                            f"Load {item['load_number'] or item['load_id']} has a packet status "
                            "or validation blocker."
                        ),
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/review-queue",
                        item["unresolved_blockers"] or item["packet_statuses"],
                    )
                )
        for item in collection_priorities[:5]:
            if int(item["age_days"]) > 30 or item["reserve_pending_amount"] != "0.00":
                recommendations.append(
                    self._recommendation(
                        "collections",
                        item["severity"],
                        item["recommended_action"],
                        (
                            f"Prioritize {item['broker_name'] or 'broker'} invoice "
                            f"{item['invoice_number'] or item['load_number'] or item['load_id']} "
                            "for collections."
                        ),
                        item["reason"],
                        item["load_id"],
                        item["load_number"],
                        "/dashboard/money",
                        item["collection_rank_reason"],
                    )
                )
        for broker in broker_insights[:3]:
            if broker["trend"] == "worsening" or broker["dispute_or_short_paid_count"] > 0:
                recommendations.append(
                    {
                        "id": f"broker_behavior:{broker['broker_id']}",
                        "type": "broker_behavior",
                        "severity": "warning",
                        "title": f"Review broker behavior: {broker['broker_name']}",
                        "description": broker["recommendation"],
                        "why": "; ".join(broker["contributing_factors"]),
                        "contributing_factors": broker["contributing_factors"],
                        "href": "/dashboard/brokers",
                        "autonomous_action": False,
                    }
                )
        for task in tasks[:3]:
            recommendations.append(
                self._recommendation(
                    "workflow_acceleration",
                    task["severity"],
                    task["title"],
                    task["description"],
                    task["description"],
                    task["load_id"],
                    task["load_number"],
                    task["href"],
                    [f"task_type={task['type']}", f"priority_score={task['priority_score']}"],
                )
            )
        deduped: dict[str, dict[str, Any]] = {}
        for item in recommendations:
            deduped.setdefault(item["id"], item)
        result = list(deduped.values())
        result.sort(key=lambda item: (-self._severity_order(item["severity"]), item["title"]))
        return result

    def _broker_behavior_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "broker_count": len(items),
            "worsening_count": sum(1 for item in items if item["trend"] == "worsening"),
            "dispute_or_short_paid_count": sum(
                int(item["dispute_or_short_paid_count"]) for item in items
            ),
            "unpaid_total": self._money(
                sum((Decimal(item["unpaid_total"]) for item in items), ZERO)
            ),
            "reserve_pending_total": self._money(
                sum((Decimal(item["reserve_pending_total"]) for item in items), ZERO)
            ),
        }

    def _insight(
        self, insight_type: str, severity: str, title: str, factors: list[str], recommendation: str
    ) -> dict[str, Any]:
        return {
            "id": f"{insight_type}:{title}",
            "type": insight_type,
            "severity": severity,
            "title": title,
            "contributing_factors": factors,
            "recommendation": recommendation,
        }

    def _recommendation(
        self,
        item_type: str,
        severity: str,
        title: str,
        description: str,
        why: str,
        load_id: str,
        load_number: str | None,
        href: str,
        factors: list[str],
    ) -> dict[str, Any]:
        return {
            "id": f"{item_type}:{load_id}:{title}",
            "type": item_type,
            "severity": severity,
            "title": title,
            "description": description,
            "why": why,
            "load_id": load_id,
            "load_number": load_number,
            "href": href,
            "contributing_factors": factors,
            "autonomous_action": False,
        }

    def _payment_reference_date(self, record: LoadPaymentRecord) -> date:
        load = record.load
        if load is not None:
            return (
                load.submitted_at.date()
                if load.submitted_at
                else load.delivery_date
                or load.pickup_date
                or self._as_aware(record.created_at).date()
            )
        return self._as_aware(record.created_at).date()

    def _risk_order(self, level: str) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level, 0)

    def _severity_order(self, severity: str) -> int:
        return {"critical": 4, "warning": 3, "info": 2}.get(severity, 1)

    def _recent_activity(self, *, org_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(COMMAND_CENTER_ACTIVITY_LIMIT)
        )
        return [
            {
                "id": str(row.id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id),
                "action": row.action,
                "created_at": self._as_aware(row.created_at).isoformat(),
            }
            for row in self.db.scalars(stmt).all()
        ]

    def _missing_documents(self, load: Load) -> list[str]:
        readiness = calculate_load_packet_readiness(load=load, db=self.db)
        return list(readiness["missing_required_documents"]["submission"])

    def _missing_doc_priority(
        self, *, load: Load, missing: list[str], blocked: bool, blocker_count: int
    ) -> int:
        score = 0
        if blocked:
            score += 35
        if DocumentType.PROOF_OF_DELIVERY.value in missing and load.status in {
            LoadStatus.DELIVERED,
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.INVOICE_READY,
        }:
            score += 45
        if DocumentType.RATE_CONFIRMATION.value in missing:
            score += 25
        if DocumentType.INVOICE.value in missing and load.status in {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.INVOICE_READY,
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
        }:
            score += 30
        if load.status in {
            LoadStatus.PACKET_REJECTED,
            LoadStatus.RESUBMISSION_NEEDED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
        }:
            score += 30
        score += min(blocker_count * 15, 30)
        return min(score, 100)

    def _collection_priority(self, record: LoadPaymentRecord, *, today: date) -> int:
        score = 0
        age = self._age_days(record, today=today)
        outstanding = self._outstanding(record)
        if age > 60:
            score += 50
        elif age > 30:
            score += 35
        elif age > 15:
            score += 20
        if outstanding >= Decimal("5000"):
            score += 30
        elif outstanding >= Decimal("1000"):
            score += 15
        if record.payment_status in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}:
            score += 35
        if (
            record.factoring_status
            in {FactoringWorkflowStatus.RESERVE_PENDING, FactoringWorkflowStatus.DISPUTED}
            or self._reserve_pending(record) > ZERO
        ):
            score += 25
        if (
            record.reconciliation_status != FactoringReconciliationStatus.RECONCILED
            and (record.amount_received or ZERO) > ZERO
        ):
            score += 15
        return min(score, 100)

    def _missing_doc_reason(
        self, *, load: Load, missing: list[str], blocked: bool, blocker_count: int
    ) -> str:
        parts: list[str] = []
        if missing:
            parts.append("Missing required submission documents: " + ", ".join(missing))
        if blocked:
            parts.append("Packet movement is blocked until required operations work is complete")
        if blocker_count:
            parts.append(f"{blocker_count} unresolved blocking validation issue(s)")
        if load.delivery_date:
            parts.append(f"Delivery date {load.delivery_date.isoformat()}")
        return "; ".join(parts) or "Load needs operational document review."

    def _collection_reason(self, record: LoadPaymentRecord, *, today: date) -> str:
        age = self._age_days(record, today=today)
        outstanding = self._money(self._outstanding(record))
        parts = [
            f"{outstanding} outstanding",
            f"{age} days since operational payment reference date",
        ]
        if record.payment_status in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}:
            parts.append(f"status is {record.payment_status.value}")
        if self._reserve_pending(record) > ZERO:
            parts.append(f"reserve pending {self._money(self._reserve_pending(record))}")
        return "; ".join(parts)

    def _missing_doc_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(doc for item in items for doc in item["missing_required_documents"])
        return {
            "total_loads": len(items),
            "blocked_from_packet_send": sum(
                1 for item in items if item["blocked_from_packet_send"]
            ),
            "by_document_type": dict(sorted(counts.items())),
            "critical_count": sum(1 for item in items if item["severity"] == "critical"),
            "warning_count": sum(1 for item in items if item["severity"] == "warning"),
        }

    def _collections_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "total_unpaid_items": len(items),
            "urgent_count": sum(1 for item in items if int(item["priority_score"]) >= 80),
            "overdue_count": sum(1 for item in items if int(item["age_days"]) > 30),
            "unpaid_total": self._money(
                sum((Decimal(item["outstanding_amount"]) for item in items), ZERO)
            ),
            "reserve_pending_total": self._money(
                sum((Decimal(item["reserve_pending_amount"]) for item in items), ZERO)
            ),
        }

    def _task_summary(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "total": len(tasks),
            "critical": sum(1 for task in tasks if task["severity"] == "critical"),
            "warning": sum(1 for task in tasks if task["severity"] == "warning"),
            "info": sum(1 for task in tasks if task["severity"] == "info"),
        }

    def _alert(
        self,
        alert_type: str,
        severity: str,
        priority: int,
        title: str,
        description: str,
        load_id: str,
        load_number: str | None,
        href: str,
    ) -> dict[str, Any]:
        return {
            "id": f"{alert_type}:{load_id}:{title}",
            "type": alert_type,
            "severity": severity,
            "priority_score": priority,
            "title": title,
            "description": description,
            "load_id": load_id,
            "load_number": load_number,
            "href": href,
        }

    def _task(
        self,
        task_type: str,
        severity: str,
        priority: int,
        title: str,
        description: str,
        load_id: str,
        load_number: str | None,
        href: str,
    ) -> dict[str, Any]:
        return {
            "id": f"{task_type}:{load_id}:{title}",
            "type": task_type,
            "severity": severity,
            "priority_score": priority,
            "title": title,
            "description": description,
            "load_id": load_id,
            "load_number": load_number,
            "href": href,
        }

    def _group_packets_by_load(
        self, packets: list[SubmissionPacket]
    ) -> dict[str, list[SubmissionPacket]]:
        grouped: dict[str, list[SubmissionPacket]] = {}
        for packet in packets:
            grouped.setdefault(str(packet.load_id), []).append(packet)
        return grouped

    def _group_blockers_by_load(
        self, blockers: list[ValidationIssue]
    ) -> dict[str, list[ValidationIssue]]:
        grouped: dict[str, list[ValidationIssue]] = {}
        for blocker in blockers:
            grouped.setdefault(str(blocker.load_id), []).append(blocker)
        return grouped

    def _packet_status(self, packet: SubmissionPacket) -> str:
        return (packet.status or "").strip().lower()

    def _outstanding(self, record: LoadPaymentRecord) -> Decimal:
        return max((record.expected_amount or ZERO) - (record.amount_received or ZERO), ZERO)

    def _reserve_pending(self, record: LoadPaymentRecord) -> Decimal:
        return max((record.reserve_amount or ZERO) - (record.reserve_paid_amount or ZERO), ZERO)

    def _age_days(self, record: LoadPaymentRecord, *, today: date) -> int:
        load = record.load
        reference = None
        if load is not None:
            reference = (
                load.submitted_at.date()
                if load.submitted_at
                else load.delivery_date or load.pickup_date
            )
        if reference is None:
            reference = self._as_aware(record.created_at).date()
        return max((today - reference).days, 0)

    def _lane_label(self, load: Load | None) -> str:
        if load is None:
            return "—"
        pickup = load.pickup_location or "Pickup TBD"
        delivery = load.delivery_location or "Delivery TBD"
        return f"{pickup} → {delivery}"

    def _severity(self, priority: int) -> str:
        if priority >= 80:
            return "critical"
        if priority >= 50:
            return "warning"
        return "info"

    def _money(self, value: Decimal) -> str:
        return str((value or ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _enum_value(self, value: Any) -> str:
        return str(getattr(value, "value", value))

    def _as_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
