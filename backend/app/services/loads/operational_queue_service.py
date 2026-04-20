from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.domain.enums.document_type import DocumentType
from app.domain.enums.load_status import LoadStatus
from app.services.loads.packet_readiness import calculate_packet_readiness


QUEUE_ORDER: tuple[str, ...] = (
    "disputed_or_short_paid",
    "payment_overdue",
    "docs_needs_attention",
    "missing_documents",
    "ready_to_invoice",
    "ready_to_submit",
    "submitted_waiting_funding",
    "advance_paid_reserve_pending",
)

FOLLOW_UP_DAYS_BY_STATUS: dict[LoadStatus, int] = {
    LoadStatus.SUBMITTED_TO_BROKER: 3,
    LoadStatus.SUBMITTED_TO_FACTORING: 3,
    LoadStatus.ADVANCE_PAID: 7,
    LoadStatus.RESERVE_PENDING: 10,
}


@dataclass(frozen=True)
class NextActionRule:
    code: str
    label: str


_NEXT_ACTIONS: dict[str, NextActionRule] = {
    "upload_pod": NextActionRule("upload_pod", "Upload POD"),
    "upload_invoice": NextActionRule("upload_invoice", "Upload invoice"),
    "fix_missing_document": NextActionRule("fix_missing_document", "Fix missing document"),
    "generate_invoice": NextActionRule("generate_invoice", "Generate invoice"),
    "submit_to_broker": NextActionRule("submit_to_broker", "Submit to broker"),
    "submit_to_factoring": NextActionRule("submit_to_factoring", "Submit to factoring"),
    "follow_up_broker": NextActionRule("follow_up_broker", "Follow up with broker"),
    "follow_up_factoring": NextActionRule("follow_up_factoring", "Follow up with factoring"),
    "review_short_pay": NextActionRule("review_short_pay", "Review short pay"),
    "resolve_dispute": NextActionRule("resolve_dispute", "Resolve dispute"),
    "monitor": NextActionRule("monitor", "Monitor load"),
}


class OperationalQueueService:
    def evaluate_load(self, load: Any, *, now: datetime | None = None) -> dict[str, Any]:
        current_time = now or datetime.now(timezone.utc)
        status = self._normalize_status(getattr(load, "status", None))
        readiness = self._build_packet_readiness(load)

        entered_at = self._state_anchor(load, status)
        days_in_state = self._days_between(entered_at, current_time)
        follow_up_days = FOLLOW_UP_DAYS_BY_STATUS.get(status)
        is_overdue = bool(follow_up_days is not None and days_in_state is not None and days_in_state >= follow_up_days)

        queue_memberships = self._queue_memberships(load, status=status, readiness=readiness, is_overdue=is_overdue)
        primary_queue = next((queue for queue in QUEUE_ORDER if queue in queue_memberships), "none")

        next_action = self._next_action(
            load,
            status=status,
            readiness=readiness,
            is_overdue=is_overdue,
        )

        priority_score = self._priority_score(
            status=status,
            primary_queue=primary_queue,
            is_overdue=is_overdue,
            days_in_state=days_in_state,
        )

        return {
            "queue": primary_queue,
            "queues": sorted(queue_memberships),
            "next_action": {
                "code": next_action.code,
                "label": next_action.label,
            },
            "days_in_state": days_in_state,
            "entered_state_at": entered_at.isoformat() if entered_at else None,
            "is_overdue": is_overdue,
            "follow_up_due_days": follow_up_days,
            "priority_score": priority_score,
            "blockers": list(readiness.get("blockers") or []),
        }

    def _build_packet_readiness(self, load: Any) -> dict[str, Any]:
        document_types: list[DocumentType] = []

        documents = getattr(load, "documents", None)
        if isinstance(documents, list):
            for document in documents:
                document_type = getattr(document, "document_type", None)
                if isinstance(document_type, DocumentType):
                    document_types.append(document_type)

        if bool(getattr(load, "has_ratecon", False)):
            document_types.append(DocumentType.RATE_CONFIRMATION)
        if bool(getattr(load, "has_bol", False)):
            document_types.append(DocumentType.BILL_OF_LADING)
            document_types.append(DocumentType.PROOF_OF_DELIVERY)
        if bool(getattr(load, "has_invoice", False)):
            document_types.append(DocumentType.INVOICE)

        return calculate_packet_readiness(document_types=document_types)

    def _queue_memberships(
        self,
        load: Any,
        *,
        status: LoadStatus,
        readiness: dict[str, Any],
        is_overdue: bool,
    ) -> set[str]:
        queues: set[str] = set()

        missing_submission = list((readiness.get("missing_required_documents") or {}).get("submission") or [])
        missing_invoice = list((readiness.get("missing_required_documents") or {}).get("invoice") or [])

        if status in {LoadStatus.SHORT_PAID, LoadStatus.DISPUTED}:
            queues.add("disputed_or_short_paid")

        if is_overdue:
            queues.add("payment_overdue")

        if status in {
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.PACKET_REJECTED,
            LoadStatus.RESUBMISSION_NEEDED,
        }:
            queues.add("docs_needs_attention")

        if missing_submission or missing_invoice:
            queues.add("missing_documents")

        if readiness.get("ready_for_invoice") and not bool(getattr(load, "has_invoice", False)):
            queues.add("ready_to_invoice")

        if readiness.get("ready_to_submit") and status in {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.INVOICE_READY,
        }:
            queues.add("ready_to_submit")

        if status in {
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
        }:
            queues.add("submitted_waiting_funding")

        if status in {LoadStatus.ADVANCE_PAID, LoadStatus.RESERVE_PENDING}:
            queues.add("advance_paid_reserve_pending")

        return queues

    def _next_action(
        self,
        load: Any,
        *,
        status: LoadStatus,
        readiness: dict[str, Any],
        is_overdue: bool,
    ) -> NextActionRule:
        missing_submission = list((readiness.get("missing_required_documents") or {}).get("submission") or [])

        if status == LoadStatus.DISPUTED:
            return _NEXT_ACTIONS["resolve_dispute"]
        if status == LoadStatus.SHORT_PAID:
            return _NEXT_ACTIONS["review_short_pay"]

        if status in {
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.PACKET_REJECTED,
            LoadStatus.RESUBMISSION_NEEDED,
        }:
            return _NEXT_ACTIONS["fix_missing_document"]

        if DocumentType.PROOF_OF_DELIVERY.value in missing_submission:
            return _NEXT_ACTIONS["upload_pod"]
        if DocumentType.INVOICE.value in missing_submission:
            if readiness.get("ready_for_invoice") and not bool(getattr(load, "has_invoice", False)):
                return _NEXT_ACTIONS["generate_invoice"]
            return _NEXT_ACTIONS["upload_invoice"]

        if status == LoadStatus.INVOICE_READY and readiness.get("ready_to_submit"):
            return _NEXT_ACTIONS["submit_to_broker"]

        if status == LoadStatus.SUBMITTED_TO_BROKER:
            return _NEXT_ACTIONS["follow_up_broker"] if is_overdue else _NEXT_ACTIONS["monitor"]

        if status in {
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.ADVANCE_PAID,
            LoadStatus.RESERVE_PENDING,
        }:
            return _NEXT_ACTIONS["follow_up_factoring"] if is_overdue else _NEXT_ACTIONS["monitor"]

        if readiness.get("ready_for_invoice") and not bool(getattr(load, "has_invoice", False)):
            return _NEXT_ACTIONS["generate_invoice"]

        return _NEXT_ACTIONS["monitor"]

    def _priority_score(
        self,
        *,
        status: LoadStatus,
        primary_queue: str,
        is_overdue: bool,
        days_in_state: int | None,
    ) -> int:
        score = 0

        if primary_queue == "payment_overdue":
            score += 100
        elif primary_queue == "disputed_or_short_paid":
            score += 95
        elif primary_queue == "ready_to_submit":
            score += 90
        elif primary_queue == "ready_to_invoice":
            score += 85
        elif primary_queue == "submitted_waiting_funding":
            score += 70
        elif primary_queue == "advance_paid_reserve_pending":
            score += 60
        elif primary_queue == "docs_needs_attention":
            score += 50
        elif primary_queue == "missing_documents":
            score += 40

        if status == LoadStatus.INVOICE_READY:
            score += 8
        if status in {LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING}:
            score += 5

        if is_overdue:
            score += 15

        if days_in_state is not None:
            score += min(days_in_state, 15)

        return score

    def _state_anchor(self, load: Any, status: LoadStatus) -> datetime | None:
        if status in {LoadStatus.SUBMITTED_TO_BROKER, LoadStatus.SUBMITTED_TO_FACTORING}:
            return self._as_datetime(getattr(load, "submitted_at", None))
        if status in {LoadStatus.ADVANCE_PAID, LoadStatus.RESERVE_PENDING}:
            return self._as_datetime(getattr(load, "funded_at", None)) or self._as_datetime(
                getattr(load, "submitted_at", None)
            )
        if status in {LoadStatus.SHORT_PAID, LoadStatus.DISPUTED}:
            return self._as_datetime(getattr(load, "paid_at", None))
        return self._as_datetime(getattr(load, "updated_at", None))

    def _as_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return None

    def _days_between(self, start: datetime | None, end: datetime) -> int | None:
        if start is None:
            return None
        delta = end - start
        return max(delta.days, 0)

    def _normalize_status(self, value: Any) -> LoadStatus:
        if isinstance(value, LoadStatus):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for status in LoadStatus:
                if normalized in {status.value.lower(), status.name.lower()}:
                    return status
        return LoadStatus.BOOKED
