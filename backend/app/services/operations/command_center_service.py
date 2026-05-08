from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.document_type import DocumentType
from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.audit_log import AuditLog
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.submission_packet import SubmissionPacket
from app.domain.models.validation_issue import ValidationIssue
from app.services.loads.packet_readiness import calculate_packet_readiness

ZERO = Decimal("0.00")
COMMAND_CENTER_LOAD_LIMIT = 200
COMMAND_CENTER_PAYMENT_LIMIT = 200
COMMAND_CENTER_ACTIVITY_LIMIT = 12

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
        today = datetime.now(timezone.utc).date()
        loads = self._load_recent_operational_loads(org_id=org_id)
        payments = self._load_payment_records(org_id=org_id)
        packets = self._load_packets(org_id=org_id)
        unresolved_blockers = self._load_unresolved_blockers(org_id=org_id)

        packet_by_load = self._group_packets_by_load(packets)
        blockers_by_load = self._group_blockers_by_load(unresolved_blockers)

        missing_docs = [self._missing_doc_item(load, packet_by_load.get(str(load.id), []), blockers_by_load.get(str(load.id), [])) for load in loads]
        missing_docs = [item for item in missing_docs if item["missing_required_documents"] or item["blocked_from_packet_send"]]
        missing_docs.sort(key=lambda item: (-int(item["priority_score"]), item["load_number"] or ""))

        collections = [self._collection_item(record, today=today) for record in payments if self._outstanding(record) > ZERO and record.payment_status in UNPAID_PAYMENT_STATUSES]
        collections.sort(key=lambda item: (-int(item["priority_score"]), -int(item["age_days"]), item["load_number"] or ""))

        alerts = self._build_alerts(
            loads=loads,
            payments=payments,
            packet_by_load=packet_by_load,
            blockers_by_load=blockers_by_load,
            missing_doc_items=missing_docs,
            today=today,
        )
        tasks = self._build_tasks(missing_doc_items=missing_docs, collection_items=collections, alerts=alerts)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kpis": self._build_kpis(
                org_id=org_id,
                loads=loads,
                payments=payments,
                packets=packets,
                unresolved_blockers=unresolved_blockers,
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
            "priority_cards": self._priority_cards(alerts=alerts, missing_docs=missing_docs, collections=collections),
            "recent_activity": self._recent_activity(org_id=org_id),
            "meta": {
                "load_limit": COMMAND_CENTER_LOAD_LIMIT,
                "payment_limit": COMMAND_CENTER_PAYMENT_LIMIT,
                "logic": "Deterministic operational prioritization based on missing required documents, packet blockers, unpaid aging, factoring reserve state, reconciliation status, and unresolved validation blockers.",
                "not_implemented": ["live GPS tracking", "telematics ingestion", "AI dispatch optimization", "websocket streaming"],
            },
        }

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

    def _build_kpis(
        self,
        *,
        org_id: str,
        loads: list[Load],
        payments: list[LoadPaymentRecord],
        packets: list[SubmissionPacket],
        unresolved_blockers: list[ValidationIssue],
        today: date,
    ) -> dict[str, Any]:
        active_loads = self.db.scalar(select(func.count()).select_from(Load).where(Load.organization_id == org_id, Load.status.in_(ACTIVE_LOAD_STATUSES))) or 0
        unpaid_total = sum((self._outstanding(record) for record in payments if record.payment_status in UNPAID_PAYMENT_STATUSES), ZERO)
        reserve_pending_total = sum((self._reserve_pending(record) for record in payments), ZERO)
        overdue = [record for record in payments if self._outstanding(record) > ZERO and self._age_days(record, today=today) > 30]
        return {
            "active_loads": int(active_loads),
            "loads_missing_docs": sum(1 for load in loads if self._missing_documents(load)),
            "overdue_invoices": len(overdue),
            "urgent_collections": sum(1 for record in payments if self._collection_priority(record, today=today) >= 80),
            "pending_packet_sends": sum(1 for packet in packets if self._packet_status(packet) in PENDING_PACKET_STATUSES),
            "unresolved_packet_intelligence_blockers": len(unresolved_blockers),
            "factoring_reserve_pending": sum(1 for record in payments if self._reserve_pending(record) > ZERO or record.factoring_status == FactoringWorkflowStatus.RESERVE_PENDING),
            "unpaid_total": self._money(unpaid_total),
            "factoring_reserve_pending_total": self._money(reserve_pending_total),
        }

    def _missing_doc_item(self, load: Load, packets: list[SubmissionPacket], blockers: list[ValidationIssue]) -> dict[str, Any]:
        missing = self._missing_documents(load)
        packet_statuses = [self._packet_status(packet) for packet in packets]
        blocked = bool(missing) or any(status in BLOCKED_PACKET_STATUSES for status in packet_statuses) or bool(blockers)
        priority = self._missing_doc_priority(load=load, missing=missing, blocked=blocked, blocker_count=len(blockers))
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
            "reason": self._missing_doc_reason(load=load, missing=missing, blocked=blocked, blocker_count=len(blockers)),
        }

    def _collection_item(self, record: LoadPaymentRecord, *, today: date) -> dict[str, Any]:
        priority = self._collection_priority(record, today=today)
        load = record.load
        return {
            "load_id": str(record.load_id),
            "load_number": load.load_number if load else None,
            "invoice_number": load.invoice_number if load else None,
            "broker_name": load.broker.name if load and load.broker else (load.broker_name_raw if load else None),
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
                alerts.append(self._alert("missing_pod", item["severity"], item["priority_score"], "Missing POD", item["reason"], item["load_id"], item["load_number"], "/dashboard/loads/" + item["load_id"]))
            if DocumentType.RATE_CONFIRMATION.value in missing:
                alerts.append(self._alert("missing_rate_confirmation", item["severity"], item["priority_score"], "Missing rate confirmation", item["reason"], item["load_id"], item["load_number"], "/dashboard/loads/" + item["load_id"]))
            if item["blocked_from_packet_send"] and (item["packet_statuses"] or item["unresolved_blockers"]):
                alerts.append(self._alert("blocked_packet_send", "critical", max(90, int(item["priority_score"])), "Packet send blocked", "Packet cannot be sent until required documents or blocking validation issues are resolved.", item["load_id"], item["load_number"], "/dashboard/loads/" + item["load_id"]))

        for record in payments:
            priority = self._collection_priority(record, today=today)
            if self._outstanding(record) > ZERO and self._age_days(record, today=today) > 30:
                alerts.append(self._alert("invoice_overdue", self._severity(priority), priority, "Invoice overdue", self._collection_reason(record, today=today), str(record.load_id), record.load.load_number if record.load else None, "/dashboard/money"))
            if record.reconciliation_status != FactoringReconciliationStatus.RECONCILED and record.amount_received and record.amount_received > ZERO:
                alerts.append(self._alert("failed_reconciliation", "warning", 70, "Reconciliation needs review", "Payment money was recorded but reconciliation is not complete.", str(record.load_id), record.load.load_number if record.load else None, "/dashboard/factoring"))
            if self._reserve_pending(record) > ZERO or record.factoring_status == FactoringWorkflowStatus.RESERVE_PENDING:
                alerts.append(self._alert("factoring_issue", "warning", 75, "Factoring reserve pending", "Factored load still has reserve dollars pending collection.", str(record.load_id), record.load.load_number if record.load else None, "/dashboard/factoring"))

        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for load in loads:
            updated_at = self._as_aware(load.updated_at)
            if load.status in {LoadStatus.BOOKED, LoadStatus.IN_TRANSIT, LoadStatus.DELIVERED} and updated_at < stale_cutoff:
                alerts.append(self._alert("stale_load_activity", "info", 35, "Stale load activity", "No operational update has been recorded in more than seven days.", str(load.id), load.load_number, "/dashboard/loads/" + str(load.id)))
            blockers = blockers_by_load.get(str(load.id), [])
            if blockers:
                alerts.append(self._alert("packet_intelligence_blocker", "critical", 90, "Packet intelligence blocker", f"{len(blockers)} unresolved blocking validation issue(s) require review.", str(load.id), load.load_number, "/dashboard/review-queue"))

        alerts.sort(key=lambda item: (-int(item["priority_score"]), item["title"], item.get("load_number") or ""))
        return alerts

    def _build_tasks(self, *, missing_doc_items: list[dict[str, Any]], collection_items: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for item in missing_doc_items:
            for doc_type in item["missing_required_documents"]:
                title = "Upload missing POD" if doc_type == DocumentType.PROOF_OF_DELIVERY.value else f"Upload missing {doc_type.replace('_', ' ')}"
                tasks.append(self._task("missing_document", item["severity"], item["priority_score"], title, item["reason"], item["load_id"], item["load_number"], "/dashboard/documents"))
            if item["blocked_from_packet_send"] and item["unresolved_blockers"]:
                tasks.append(self._task("review_blocked_packet", "critical", max(90, int(item["priority_score"])), "Review blocked packet", "Resolve packet intelligence blockers before resending.", item["load_id"], item["load_number"], "/dashboard/review-queue"))
            elif not item["missing_required_documents"] and item["blocked_from_packet_send"]:
                tasks.append(self._task("resend_packet", item["severity"], item["priority_score"], "Resend packet", "Packet status indicates retry or review is needed.", item["load_id"], item["load_number"], "/dashboard/loads/" + item["load_id"]))

        for item in collection_items[:15]:
            if int(item["age_days"]) > 30:
                tasks.append(self._task("follow_up_overdue_invoice", item["severity"], item["priority_score"], "Follow up overdue invoice", item["reason"], item["load_id"], item["load_number"], "/dashboard/money"))
            if item["reconciliation_status"] != FactoringReconciliationStatus.RECONCILED.value and item["amount_received"] != "0.00":
                tasks.append(self._task("reconcile_payment", "warning", 70, "Reconcile payment", "Payment has been received but reconciliation remains open.", item["load_id"], item["load_number"], "/dashboard/factoring"))
            if item["reserve_pending_amount"] != "0.00":
                tasks.append(self._task("review_factoring_reserve", "warning", 75, "Review factoring reserve", "Reserve balance is still pending release.", item["load_id"], item["load_number"], "/dashboard/factoring"))

        for alert in alerts:
            if alert["type"] == "stale_load_activity":
                tasks.append(self._task("review_load_activity", "info", 35, "Review stale load", alert["description"], alert["load_id"], alert["load_number"], alert["href"]))

        deduped: dict[str, dict[str, Any]] = {}
        for task in tasks:
            deduped.setdefault(f"{task['type']}:{task['load_id']}:{task['title']}", task)
        result = list(deduped.values())
        result.sort(key=lambda item: (-int(item["priority_score"]), item["title"], item.get("load_number") or ""))
        return result

    def _priority_cards(self, *, alerts: list[dict[str, Any]], missing_docs: list[dict[str, Any]], collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        critical_alerts = [alert for alert in alerts if alert["severity"] == "critical"]
        blocked_packets = [item for item in missing_docs if item["blocked_from_packet_send"]]
        urgent_collections = [item for item in collections if int(item["priority_score"]) >= 80]
        return [
            {"key": "critical_alerts", "label": "Critical operational alerts", "count": len(critical_alerts), "severity": "critical", "next_action": "Work these first; they block collections or packet movement."},
            {"key": "blocked_packets", "label": "Blocked packet sends", "count": len(blocked_packets), "severity": "critical" if blocked_packets else "info", "next_action": "Resolve required documents and validation blockers."},
            {"key": "urgent_collections", "label": "Urgent collections", "count": len(urgent_collections), "severity": "critical" if urgent_collections else "info", "next_action": "Follow up oldest and highest-risk unpaid invoices."},
            {"key": "missing_docs", "label": "Loads missing docs", "count": len(missing_docs), "severity": "warning" if missing_docs else "info", "next_action": "Upload PODs, invoices, and rate confirmations."},
        ]

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
        document_types = [document.document_type for document in load.documents if document.processing_status != ProcessingStatus.FAILED]
        readiness = calculate_packet_readiness(document_types=document_types)
        return list(readiness["missing_required_documents"]["submission"])

    def _missing_doc_priority(self, *, load: Load, missing: list[str], blocked: bool, blocker_count: int) -> int:
        score = 0
        if blocked:
            score += 35
        if DocumentType.PROOF_OF_DELIVERY.value in missing and load.status in {LoadStatus.DELIVERED, LoadStatus.DOCS_RECEIVED, LoadStatus.DOCS_NEEDS_ATTENTION, LoadStatus.INVOICE_READY}:
            score += 45
        if DocumentType.RATE_CONFIRMATION.value in missing:
            score += 25
        if DocumentType.INVOICE.value in missing and load.status in {LoadStatus.DOCS_RECEIVED, LoadStatus.INVOICE_READY, LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING}:
            score += 30
        if load.status in {LoadStatus.PACKET_REJECTED, LoadStatus.RESUBMISSION_NEEDED, LoadStatus.DOCS_NEEDS_ATTENTION}:
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
        if record.factoring_status in {FactoringWorkflowStatus.RESERVE_PENDING, FactoringWorkflowStatus.DISPUTED} or self._reserve_pending(record) > ZERO:
            score += 25
        if record.reconciliation_status != FactoringReconciliationStatus.RECONCILED and (record.amount_received or ZERO) > ZERO:
            score += 15
        return min(score, 100)

    def _missing_doc_reason(self, *, load: Load, missing: list[str], blocked: bool, blocker_count: int) -> str:
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
        parts = [f"{outstanding} outstanding", f"{age} days since operational payment reference date"]
        if record.payment_status in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}:
            parts.append(f"status is {record.payment_status.value}")
        if self._reserve_pending(record) > ZERO:
            parts.append(f"reserve pending {self._money(self._reserve_pending(record))}")
        return "; ".join(parts)

    def _missing_doc_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(doc for item in items for doc in item["missing_required_documents"])
        return {
            "total_loads": len(items),
            "blocked_from_packet_send": sum(1 for item in items if item["blocked_from_packet_send"]),
            "by_document_type": dict(sorted(counts.items())),
            "critical_count": sum(1 for item in items if item["severity"] == "critical"),
            "warning_count": sum(1 for item in items if item["severity"] == "warning"),
        }

    def _collections_summary(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "total_unpaid_items": len(items),
            "urgent_count": sum(1 for item in items if int(item["priority_score"]) >= 80),
            "overdue_count": sum(1 for item in items if int(item["age_days"]) > 30),
            "unpaid_total": self._money(sum((Decimal(item["outstanding_amount"]) for item in items), ZERO)),
            "reserve_pending_total": self._money(sum((Decimal(item["reserve_pending_amount"]) for item in items), ZERO)),
        }

    def _task_summary(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "total": len(tasks),
            "critical": sum(1 for task in tasks if task["severity"] == "critical"),
            "warning": sum(1 for task in tasks if task["severity"] == "warning"),
            "info": sum(1 for task in tasks if task["severity"] == "info"),
        }

    def _alert(self, alert_type: str, severity: str, priority: int, title: str, description: str, load_id: str, load_number: str | None, href: str) -> dict[str, Any]:
        return {"id": f"{alert_type}:{load_id}:{title}", "type": alert_type, "severity": severity, "priority_score": priority, "title": title, "description": description, "load_id": load_id, "load_number": load_number, "href": href}

    def _task(self, task_type: str, severity: str, priority: int, title: str, description: str, load_id: str, load_number: str | None, href: str) -> dict[str, Any]:
        return {"id": f"{task_type}:{load_id}:{title}", "type": task_type, "severity": severity, "priority_score": priority, "title": title, "description": description, "load_id": load_id, "load_number": load_number, "href": href}

    def _group_packets_by_load(self, packets: list[SubmissionPacket]) -> dict[str, list[SubmissionPacket]]:
        grouped: dict[str, list[SubmissionPacket]] = {}
        for packet in packets:
            grouped.setdefault(str(packet.load_id), []).append(packet)
        return grouped

    def _group_blockers_by_load(self, blockers: list[ValidationIssue]) -> dict[str, list[ValidationIssue]]:
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
            reference = load.submitted_at.date() if load.submitted_at else load.delivery_date or load.pickup_date
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
