from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.enums.follow_up_task import FollowUpTaskPriority, FollowUpTaskStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.follow_up_task import FollowUpTask
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.submission_packet import SubmissionPacket


ZERO = Decimal("0")
OVERDUE_THRESHOLD_DAYS = 30


class MoneyDashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_money_dashboard(
        self,
        org_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, object]:
        payment_records = self._load_payment_records(org_id)
        if not payment_records:
            return {
                "summary": self._empty_summary(),
                "aging_buckets": self._empty_aging_buckets(),
                "status_breakdown": self._empty_status_breakdown(),
                "factoring_vs_direct": self._empty_factoring_vs_direct(),
                "needs_attention": self._needs_attention(org_id),
                "recent_cash_activity": [],
            }

        load_ids = [record.load_id for record in payment_records]
        loads = self._load_loads(org_id, load_ids)
        packets = self._latest_submission_sent_by_load(org_id, load_ids)

        now = datetime.now(timezone.utc)
        status_breakdown: dict[str, dict[str, Decimal | int | str]] = defaultdict(
            lambda: {"status": "", "count": 0, "amount": ZERO}
        )
        aging_buckets = {
            "0_30": {"bucket": "0-30", "count": 0, "amount": ZERO},
            "31_60": {"bucket": "31-60", "count": 0, "amount": ZERO},
            "61_90": {"bucket": "61-90", "count": 0, "amount": ZERO},
            "90_plus": {"bucket": "90+", "count": 0, "amount": ZERO},
        }

        total_expected = ZERO
        total_received = ZERO
        overdue_amount = ZERO
        paid_amount = ZERO
        unpaid_count = 0
        overdue_count = 0
        disputed_count = 0
        short_paid_count = 0
        reserve_pending_amount = ZERO
        factoring_advance_amount = ZERO
        factoring_loads_count = 0
        factoring_total = ZERO
        direct_loads_count = 0
        direct_total = ZERO
        direct_unpaid_total = ZERO

        filtered_records = 0

        for record in payment_records:
            load = loads.get(record.load_id)
            reference_date = self._aging_reference_date(record=record, load=load, packet_sent_at=packets.get(record.load_id))

            if not self._within_range(reference_date, date_from=date_from, date_to=date_to):
                continue

            filtered_records += 1

            expected_amount = record.expected_amount or ZERO
            amount_received = record.amount_received or ZERO
            outstanding_amount = max(expected_amount - amount_received, ZERO)

            total_expected += expected_amount
            total_received += amount_received

            status_key = record.payment_status.value
            status_row = status_breakdown[status_key]
            status_row["status"] = status_key
            status_row["count"] = int(status_row["count"]) + 1
            status_row["amount"] = Decimal(str(status_row["amount"])) + expected_amount

            if record.payment_status == LoadPaymentStatus.PAID:
                paid_amount += amount_received
            else:
                unpaid_count += 1

            if record.payment_status == LoadPaymentStatus.DISPUTED:
                disputed_count += 1
            if record.payment_status == LoadPaymentStatus.SHORT_PAID:
                short_paid_count += 1

            if record.payment_status == LoadPaymentStatus.RESERVE_PENDING:
                reserve_pending_amount += (record.reserve_amount or ZERO) - (record.reserve_paid_amount or ZERO)

            if record.factoring_used:
                factoring_loads_count += 1
                factoring_total += expected_amount
                factoring_advance_amount += record.advance_amount or ZERO
            else:
                direct_loads_count += 1
                direct_total += expected_amount
                if record.payment_status != LoadPaymentStatus.PAID:
                    direct_unpaid_total += outstanding_amount

            age_days = max((now.date() - reference_date).days, 0)
            bucket_key = self._age_bucket_key(age_days)
            aging_buckets[bucket_key]["count"] = int(aging_buckets[bucket_key]["count"]) + 1
            aging_buckets[bucket_key]["amount"] = Decimal(str(aging_buckets[bucket_key]["amount"])) + outstanding_amount

            if age_days > OVERDUE_THRESHOLD_DAYS and record.payment_status != LoadPaymentStatus.PAID and outstanding_amount > ZERO:
                overdue_count += 1
                overdue_amount += outstanding_amount

        total_outstanding = max(total_expected - total_received, ZERO)

        summary = {
            "total_receivables": str(total_outstanding),
            "total_expected": str(total_expected),
            "total_received": str(total_received),
            "total_outstanding": str(total_outstanding),
            "overdue_amount": str(overdue_amount),
            "paid_amount": str(paid_amount),
            "unpaid_count": unpaid_count,
            "overdue_count": overdue_count,
            "disputed_count": disputed_count,
            "short_paid_count": short_paid_count,
            "reserve_pending_amount": str(max(reserve_pending_amount, ZERO)),
            "factoring_advance_amount": str(factoring_advance_amount),
            "invoices_pending": max(unpaid_count, 0),
            "cash_collected": str(total_received),
        }

        normalized_status_breakdown = [
            {
                "status": row["status"],
                "count": int(row["count"]),
                "amount": str(Decimal(str(row["amount"]))),
            }
            for row in sorted(status_breakdown.values(), key=lambda item: str(item["status"]))
        ]

        if filtered_records == 0:
            normalized_status_breakdown = self._empty_status_breakdown()

        return {
            "summary": summary,
            "aging_buckets": [
                {"bucket": item["bucket"], "count": int(item["count"]), "amount": str(Decimal(str(item["amount"])))}
                for item in aging_buckets.values()
            ],
            "status_breakdown": normalized_status_breakdown,
            "factoring_vs_direct": {
                "factored": {
                    "count": factoring_loads_count,
                    "amount": str(factoring_total),
                },
                "direct": {
                    "count": direct_loads_count,
                    "amount": str(direct_total),
                },
                "advance_total": str(factoring_advance_amount),
                "reserve_pending_total": str(max(reserve_pending_amount, ZERO)),
                "direct_unpaid_total": str(direct_unpaid_total),
            },
            "needs_attention": self._needs_attention(org_id),
            "recent_cash_activity": self._recent_cash_activity(payment_records, loads=loads, date_from=date_from, date_to=date_to),
        }

    def _load_payment_records(self, org_id: str) -> list[LoadPaymentRecord]:
        stmt: Select[tuple[LoadPaymentRecord]] = (
            select(LoadPaymentRecord)
            .where(LoadPaymentRecord.organization_id == org_id)
            .order_by(LoadPaymentRecord.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def _load_loads(self, org_id: str, load_ids: list[object]) -> dict[object, Load]:
        stmt: Select[tuple[Load]] = select(Load).where(Load.organization_id == org_id).where(Load.id.in_(load_ids))
        return {item.id: item for item in self.db.execute(stmt).scalars().all()}

    def _latest_submission_sent_by_load(self, org_id: str, load_ids: list[object]) -> dict[object, datetime]:
        stmt: Select[tuple[SubmissionPacket]] = (
            select(SubmissionPacket)
            .where(SubmissionPacket.organization_id == org_id)
            .where(SubmissionPacket.load_id.in_(load_ids))
            .where(SubmissionPacket.sent_at.is_not(None))
            .order_by(SubmissionPacket.load_id, SubmissionPacket.sent_at.desc())
        )
        latest_by_load: dict[object, datetime] = {}
        for packet in self.db.execute(stmt).scalars().all():
            if packet.load_id not in latest_by_load and packet.sent_at is not None:
                latest_by_load[packet.load_id] = packet.sent_at
        return latest_by_load

    def _needs_attention(self, org_id: str) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        stmt: Select[tuple[FollowUpTask]] = (
            select(FollowUpTask)
            .where(FollowUpTask.organization_id == org_id)
            .where(FollowUpTask.status == FollowUpTaskStatus.OPEN)
            .where(FollowUpTask.due_at <= now)
            .order_by(FollowUpTask.priority.desc(), FollowUpTask.due_at.asc())
            .limit(10)
        )
        tasks = list(self.db.execute(stmt).scalars().all())

        load_ids = [task.load_id for task in tasks]
        load_map = self._load_loads(org_id, load_ids) if load_ids else {}

        return {
            "urgent_count": sum(1 for item in tasks if item.priority == FollowUpTaskPriority.URGENT),
            "overdue_followups_count": len(tasks),
            "top_items": [
                {
                    "load_id": str(item.load_id),
                    "load_number": load_map.get(item.load_id).load_number if load_map.get(item.load_id) else None,
                    "task_type": item.task_type.value,
                    "priority": item.priority.value,
                    "due_at": item.due_at.isoformat(),
                    "recommended_action": item.recommended_action,
                }
                for item in tasks
            ],
        }

    def _recent_cash_activity(
        self,
        records: list[LoadPaymentRecord],
        *,
        loads: dict[object, Load],
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for record in records:
            if record.amount_received <= ZERO:
                continue
            paid_date = record.paid_date or record.updated_at
            if paid_date is None:
                continue
            if not self._within_range(paid_date.date(), date_from=date_from, date_to=date_to):
                continue
            load = loads.get(record.load_id)
            items.append(
                {
                    "load_number": load.load_number if load else None,
                    "amount_received": str(record.amount_received),
                    "paid_date": paid_date.isoformat(),
                    "payment_status": record.payment_status.value,
                    "factoring_used": bool(record.factoring_used),
                }
            )

        return sorted(items, key=lambda item: str(item["paid_date"]), reverse=True)[:10]

    def _aging_reference_date(
        self,
        *,
        record: LoadPaymentRecord,
        load: Load | None,
        packet_sent_at: datetime | None,
    ) -> date:
        # Aging basis fallback order:
        # 1) latest submission packet sent_at (submitted/sent context)
        # 2) load submitted_at / created_at when no submission packet exists
        # 3) payment record updated_at / created_at as final fallback for legacy data
        if packet_sent_at is not None:
            return packet_sent_at.date()

        if load is not None:
            if load.submitted_at is not None:
                return load.submitted_at.date()
            if load.created_at is not None:
                return load.created_at.date()

        if record.updated_at is not None:
            return record.updated_at.date()
        return record.created_at.date()

    def _within_range(self, value: date, *, date_from: date | None, date_to: date | None) -> bool:
        if date_from and value < date_from:
            return False
        if date_to and value > date_to:
            return False
        return True

    def _age_bucket_key(self, age_days: int) -> str:
        if age_days <= 30:
            return "0_30"
        if age_days <= 60:
            return "31_60"
        if age_days <= 90:
            return "61_90"
        return "90_plus"

    def _empty_summary(self) -> dict[str, object]:
        return {
            "total_receivables": "0",
            "total_expected": "0",
            "total_received": "0",
            "total_outstanding": "0",
            "overdue_amount": "0",
            "paid_amount": "0",
            "unpaid_count": 0,
            "overdue_count": 0,
            "disputed_count": 0,
            "short_paid_count": 0,
            "reserve_pending_amount": "0",
            "factoring_advance_amount": "0",
            "invoices_pending": 0,
            "cash_collected": "0",
        }

    def _empty_aging_buckets(self) -> list[dict[str, object]]:
        return [
            {"bucket": "0-30", "count": 0, "amount": "0"},
            {"bucket": "31-60", "count": 0, "amount": "0"},
            {"bucket": "61-90", "count": 0, "amount": "0"},
            {"bucket": "90+", "count": 0, "amount": "0"},
        ]

    def _empty_status_breakdown(self) -> list[dict[str, object]]:
        return [
            {"status": status.value, "count": 0, "amount": "0"}
            for status in LoadPaymentStatus
        ]

    def _empty_factoring_vs_direct(self) -> dict[str, object]:
        return {
            "factored": {"count": 0, "amount": "0"},
            "direct": {"count": 0, "amount": "0"},
            "advance_total": "0",
            "reserve_pending_total": "0",
            "direct_unpaid_total": "0",
        }
