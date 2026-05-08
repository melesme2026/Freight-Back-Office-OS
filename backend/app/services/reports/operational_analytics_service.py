from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord

ZERO = Decimal("0.00")
PAID_STATUSES = {LoadPaymentStatus.PAID}
UNPAID_STATUSES = {
    LoadPaymentStatus.NOT_SUBMITTED,
    LoadPaymentStatus.SUBMITTED,
    LoadPaymentStatus.AWAITING_PAYMENT,
    LoadPaymentStatus.PARTIALLY_PAID,
    LoadPaymentStatus.ADVANCE_PAID,
    LoadPaymentStatus.RESERVE_PENDING,
    LoadPaymentStatus.SHORT_PAID,
    LoadPaymentStatus.DISPUTED,
}
PARTIAL_STATUSES = {
    LoadPaymentStatus.PARTIALLY_PAID,
    LoadPaymentStatus.ADVANCE_PAID,
    LoadPaymentStatus.RESERVE_PENDING,
    LoadPaymentStatus.SHORT_PAID,
}
AGING_BUCKETS = (
    ("current", "Current", 0, 0),
    ("1_15", "1–15", 1, 15),
    ("16_30", "16–30", 16, 30),
    ("31_60", "31–60", 31, 60),
    ("60_plus", "60+", 61, None),
)


class OperationalAnalyticsService:
    """Lightweight operational analytics over load payment records.

    The service intentionally uses deterministic receivables math only. Driver and lane
    profitability are represented as revenue, collections, factoring, and aging exposure;
    no margin is calculated because no actual expense model exists in this domain.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_operational_analytics(
        self,
        *,
        org_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        broker_id: str | None = None,
        driver_id: str | None = None,
        factoring_status: str | None = None,
    ) -> dict[str, Any]:
        rows = self._load_rows(
            org_id=org_id,
            date_from=date_from,
            date_to=date_to,
            broker_id=broker_id,
            driver_id=driver_id,
            factoring_status=factoring_status,
        )
        today = datetime.now(timezone.utc).date()

        revenue = self._build_revenue(rows)
        aging = self._build_aging(rows, today=today)
        unpaid = self._build_unpaid(rows, today=today)
        collections = self._build_collections(rows, today=today)

        return {
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "broker_id": broker_id,
                "driver_id": driver_id,
                "factoring_status": factoring_status,
            },
            "metric_definitions": {
                "revenue": "Sum of load payment record expected_amount for loads in the selected date range.",
                "paid_revenue": "Sum of amount_received for records with payment_status=paid.",
                "unpaid_revenue": "Sum of max(expected_amount - amount_received, 0) for records that are not fully paid.",
                "factored_revenue": "Sum of expected_amount where factoring_used is true or factoring_status is not not_factored.",
                "aging": "Days since submitted_at, otherwise delivery_date, pickup_date, or record created_at for unpaid balances.",
                "profitability": "Revenue and collection performance only; margin is not calculated without actual expense data.",
            },
            "revenue": revenue,
            "unpaid_invoices": unpaid,
            "aging_report": aging,
            "driver_profitability": self._group_by_driver(rows, today=today),
            "broker_performance": self._group_by_broker(rows, today=today),
            "lane_profitability": self._group_by_lane(rows, today=today),
            "collections": collections,
            "filter_options": self._filter_options(org_id),
        }

    def _load_rows(
        self,
        *,
        org_id: str,
        date_from: date | None,
        date_to: date | None,
        broker_id: str | None,
        driver_id: str | None,
        factoring_status: str | None,
    ) -> list[LoadPaymentRecord]:
        stmt = (
            select(LoadPaymentRecord)
            .join(Load, Load.id == LoadPaymentRecord.load_id)
            .where(LoadPaymentRecord.organization_id == org_id)
            .options(
                selectinload(LoadPaymentRecord.load).selectinload(Load.driver),
                selectinload(LoadPaymentRecord.load).selectinload(Load.broker),
            )
            .order_by(LoadPaymentRecord.created_at.desc())
        )
        if broker_id:
            stmt = stmt.where(Load.broker_id == broker_id)
        if driver_id:
            stmt = stmt.where(Load.driver_id == driver_id)
        if factoring_status:
            stmt = stmt.where(LoadPaymentRecord.factoring_status == self._coerce_factoring_status(factoring_status))

        records = list(self.db.scalars(stmt).unique().all())
        filtered: list[LoadPaymentRecord] = []
        for record in records:
            reference_date = self._reference_date(record)
            if date_from and reference_date < date_from:
                continue
            if date_to and reference_date > date_to:
                continue
            filtered.append(record)
        return filtered

    def _filter_options(self, org_id: str) -> dict[str, Any]:
        records = self._load_rows(
            org_id=org_id,
            date_from=None,
            date_to=None,
            broker_id=None,
            driver_id=None,
            factoring_status=None,
        )
        brokers: dict[str, str] = {}
        drivers: dict[str, str] = {}
        for record in records:
            load = record.load
            if load.broker_id:
                brokers[str(load.broker_id)] = load.broker.name if load.broker else (load.broker_name_raw or "Unknown broker")
            if load.driver_id:
                drivers[str(load.driver_id)] = load.driver.full_name if load.driver else "Unknown driver"
        return {
            "brokers": [{"id": key, "name": brokers[key]} for key in sorted(brokers, key=lambda item: brokers[item].lower())],
            "drivers": [{"id": key, "name": drivers[key]} for key in sorted(drivers, key=lambda item: drivers[item].lower())],
            "factoring_statuses": [status.value for status in FactoringWorkflowStatus],
        }

    def _build_revenue(self, records: list[LoadPaymentRecord]) -> dict[str, Any]:
        total = sum((self._expected(record) for record in records), ZERO)
        received = sum((self._received(record) for record in records), ZERO)
        paid = sum((self._received(record) for record in records if record.payment_status in PAID_STATUSES), ZERO)
        unpaid = sum((self._outstanding(record) for record in records if record.payment_status in UNPAID_STATUSES), ZERO)
        factored = sum((self._expected(record) for record in records if self._is_factored(record)), ZERO)
        invoice_count = len(records)
        average = total / invoice_count if invoice_count else ZERO
        trends: dict[str, dict[str, Any]] = defaultdict(lambda: {"month": "", "revenue": ZERO, "paid_revenue": ZERO, "unpaid_revenue": ZERO, "invoice_count": 0})
        for record in records:
            month = self._reference_date(record).strftime("%Y-%m")
            row = trends[month]
            row["month"] = month
            row["revenue"] += self._expected(record)
            row["paid_revenue"] += self._received(record) if record.payment_status in PAID_STATUSES else ZERO
            row["unpaid_revenue"] += self._outstanding(record) if record.payment_status in UNPAID_STATUSES else ZERO
            row["invoice_count"] += 1
        return {
            "total_revenue": self._money(total),
            "paid_revenue": self._money(paid),
            "received_revenue": self._money(received),
            "unpaid_revenue": self._money(unpaid),
            "factored_revenue": self._money(factored),
            "invoice_count": invoice_count,
            "average_invoice_amount": self._money(average),
            "monthly_trends": [self._serialize_row(row) for _, row in sorted(trends.items())],
        }

    def _build_unpaid(self, records: list[LoadPaymentRecord], *, today: date) -> dict[str, Any]:
        unpaid_records = [record for record in records if self._outstanding(record) > ZERO and record.payment_status in UNPAID_STATUSES]
        overdue_records = [record for record in unpaid_records if self._age_days(record, today=today) > 0]
        partial_records = [record for record in unpaid_records if record.payment_status in PARTIAL_STATUSES]
        return {
            "unpaid_count": len(unpaid_records),
            "partially_paid_count": len(partial_records),
            "overdue_count": len(overdue_records),
            "unpaid_total": self._money(sum((self._outstanding(record) for record in unpaid_records), ZERO)),
            "partially_paid_total": self._money(sum((self._outstanding(record) for record in partial_records), ZERO)),
            "overdue_total": self._money(sum((self._outstanding(record) for record in overdue_records), ZERO)),
            "items": [self._invoice_item(record, today=today) for record in sorted(unpaid_records, key=lambda item: self._age_days(item, today=today), reverse=True)[:50]],
        }

    def _build_aging(self, records: list[LoadPaymentRecord], *, today: date) -> dict[str, Any]:
        buckets = {key: {"bucket": key, "label": label, "count": 0, "balance": ZERO} for key, label, _, _ in AGING_BUCKETS}
        for record in records:
            balance = self._outstanding(record)
            if balance <= ZERO or record.payment_status not in UNPAID_STATUSES:
                continue
            key = self._aging_bucket(self._age_days(record, today=today))
            buckets[key]["count"] += 1
            buckets[key]["balance"] += balance
        rows = [self._serialize_row(buckets[key]) for key, _, _, _ in AGING_BUCKETS]
        return {
            "buckets": rows,
            "total_count": sum(int(row["count"]) for row in rows),
            "total_balance": self._money(sum((Decimal(str(row["balance"])) for row in rows), ZERO)),
        }

    def _build_collections(self, records: list[LoadPaymentRecord], *, today: date) -> dict[str, Any]:
        unpaid_records = [record for record in records if self._outstanding(record) > ZERO and record.payment_status in UNPAID_STATUSES]
        overdue_records = [record for record in unpaid_records if self._age_days(record, today=today) > 0]
        reserve_pending = sum((max((record.reserve_amount or ZERO) - (record.reserve_paid_amount or ZERO), ZERO) for record in records), ZERO)
        unreconciled = [record for record in records if record.reconciliation_status != FactoringReconciliationStatus.RECONCILED]
        return {
            "unpaid_total": self._money(sum((self._outstanding(record) for record in unpaid_records), ZERO)),
            "overdue_balance": self._money(sum((self._outstanding(record) for record in overdue_records), ZERO)),
            "reserve_pending_total": self._money(reserve_pending),
            "unreconciled_count": len(unreconciled),
            "unreconciled_balance": self._money(sum((self._outstanding(record) for record in unreconciled), ZERO)),
            "dispute_count": sum(1 for record in records if record.payment_status == LoadPaymentStatus.DISPUTED),
            "short_paid_count": sum(1 for record in records if record.payment_status == LoadPaymentStatus.SHORT_PAID),
            "risk_summary": self._risk_summary(unpaid_records, today=today),
            "oldest_invoices": [self._invoice_item(record, today=today) for record in sorted(unpaid_records, key=lambda item: self._age_days(item, today=today), reverse=True)[:10]],
        }

    def _group_by_driver(self, records: list[LoadPaymentRecord], *, today: date) -> list[dict[str, Any]]:
        return self._group_records(records, today=today, key_func=lambda record: (str(record.load.driver_id), record.load.driver.full_name if record.load.driver else "Unknown driver"))

    def _group_by_broker(self, records: list[LoadPaymentRecord], *, today: date) -> list[dict[str, Any]]:
        return self._group_records(records, today=today, key_func=lambda record: (str(record.load.broker_id) if record.load.broker_id else "unassigned", record.load.broker.name if record.load.broker else (record.load.broker_name_raw or "Unassigned broker")), include_payment_speed=True)

    def _group_by_lane(self, records: list[LoadPaymentRecord], *, today: date) -> list[dict[str, Any]]:
        return self._group_records(records, today=today, key_func=lambda record: (self._lane_key(record.load), self._lane_label(record.load)))

    def _group_records(self, records: list[LoadPaymentRecord], *, today: date, key_func, include_payment_speed: bool = False) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        paid_speed_days: dict[str, list[int]] = defaultdict(list)
        for record in records:
            key, label = key_func(record)
            row = grouped.setdefault(key, {"id": key, "name": label, "revenue": ZERO, "paid_revenue": ZERO, "unpaid_balance": ZERO, "factored_revenue": ZERO, "load_count": 0, "overdue_balance": ZERO, "overdue_count": 0, "dispute_count": 0, "unreconciled_count": 0})
            row["revenue"] += self._expected(record)
            row["paid_revenue"] += self._received(record) if record.payment_status in PAID_STATUSES else ZERO
            row["unpaid_balance"] += self._outstanding(record) if record.payment_status in UNPAID_STATUSES else ZERO
            row["factored_revenue"] += self._expected(record) if self._is_factored(record) else ZERO
            row["load_count"] += 1
            if self._age_days(record, today=today) > 0 and self._outstanding(record) > ZERO:
                row["overdue_balance"] += self._outstanding(record)
                row["overdue_count"] += 1
            if record.payment_status == LoadPaymentStatus.DISPUTED:
                row["dispute_count"] += 1
            if record.reconciliation_status != FactoringReconciliationStatus.RECONCILED:
                row["unreconciled_count"] += 1
            if include_payment_speed and record.paid_date:
                paid_speed_days[key].append(max((record.paid_date.date() - self._reference_date(record)).days, 0))
        rows = []
        for key, row in grouped.items():
            load_count = int(row["load_count"])
            row["average_load_value"] = row["revenue"] / load_count if load_count else ZERO
            row["profitability_note"] = "Revenue-only view; margin is not calculated because actual expenses are not available."
            if include_payment_speed:
                speeds = paid_speed_days.get(key, [])
                row["average_payment_days"] = round(sum(speeds) / len(speeds), 1) if speeds else None
            rows.append(self._serialize_row(row))
        return sorted(rows, key=lambda row: Decimal(str(row["revenue"])), reverse=True)[:25]

    def _risk_summary(self, records: list[LoadPaymentRecord], *, today: date) -> dict[str, Any]:
        high = [record for record in records if self._age_days(record, today=today) > 60 or record.payment_status in {LoadPaymentStatus.DISPUTED, LoadPaymentStatus.SHORT_PAID}]
        medium = [record for record in records if 31 <= self._age_days(record, today=today) <= 60]
        low = [record for record in records if self._age_days(record, today=today) <= 30]
        return {
            "high_risk_count": len(high),
            "high_risk_balance": self._money(sum((self._outstanding(record) for record in high), ZERO)),
            "medium_risk_count": len(medium),
            "medium_risk_balance": self._money(sum((self._outstanding(record) for record in medium), ZERO)),
            "low_risk_count": len(low),
            "low_risk_balance": self._money(sum((self._outstanding(record) for record in low), ZERO)),
        }

    def _invoice_item(self, record: LoadPaymentRecord, *, today: date) -> dict[str, Any]:
        load = record.load
        return {
            "load_id": str(load.id),
            "load_number": load.load_number,
            "invoice_number": load.invoice_number,
            "broker_name": load.broker.name if load.broker else load.broker_name_raw,
            "driver_name": load.driver.full_name if load.driver else None,
            "lane": self._lane_label(load),
            "payment_status": record.payment_status.value,
            "factoring_status": record.factoring_status.value,
            "reconciliation_status": record.reconciliation_status.value,
            "expected_amount": self._money(self._expected(record)),
            "amount_received": self._money(self._received(record)),
            "outstanding_amount": self._money(self._outstanding(record)),
            "age_days": self._age_days(record, today=today),
            "reference_date": self._reference_date(record).isoformat(),
        }

    def _reference_date(self, record: LoadPaymentRecord) -> date:
        load = record.load
        if load.submitted_at:
            return load.submitted_at.date()
        if load.delivery_date:
            return load.delivery_date
        if load.pickup_date:
            return load.pickup_date
        return record.created_at.date()

    def _age_days(self, record: LoadPaymentRecord, *, today: date) -> int:
        if self._outstanding(record) <= ZERO or record.payment_status in PAID_STATUSES:
            return 0
        return max((today - self._reference_date(record)).days, 0)

    def _aging_bucket(self, days: int) -> str:
        for key, _, minimum, maximum in AGING_BUCKETS:
            if maximum is None and days >= minimum:
                return key
            if maximum is not None and minimum <= days <= maximum:
                return key
        return "current"

    def _lane_key(self, load: Load) -> str:
        return f"{self._normalize_location(load.pickup_location)}->{self._normalize_location(load.delivery_location)}"

    def _lane_label(self, load: Load) -> str:
        pickup = load.pickup_location or "Unknown pickup"
        delivery = load.delivery_location or "Unknown delivery"
        return f"{pickup} → {delivery}"

    def _normalize_location(self, value: str | None) -> str:
        return (value or "unknown").strip().lower()

    def _coerce_factoring_status(self, value: str) -> FactoringWorkflowStatus:
        return FactoringWorkflowStatus(value)

    def _is_factored(self, record: LoadPaymentRecord) -> bool:
        return bool(record.factoring_used or record.factoring_status != FactoringWorkflowStatus.NOT_FACTORED)

    def _expected(self, record: LoadPaymentRecord) -> Decimal:
        return record.expected_amount or ZERO

    def _received(self, record: LoadPaymentRecord) -> Decimal:
        return record.amount_received or ZERO

    def _outstanding(self, record: LoadPaymentRecord) -> Decimal:
        return max(self._expected(record) - self._received(record), ZERO)

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: self._money(value) if isinstance(value, Decimal) else value for key, value in row.items()}

    def _money(self, value: Decimal) -> str:
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
