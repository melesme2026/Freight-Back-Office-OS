from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from app.domain.models.accounting import (
    AccountingExportMapping,
    AccountingIntegrationSettings,
)
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.core.exceptions import ValidationError
from app.services.accounting.quickbooks_service import QuickBooksIntegrationService
from app.services.organizations.quota_service import OrganizationQuotaService
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

AccountingExportKind = Literal["invoices", "factoring", "settlements", "payments", "aging"]
ZERO = Decimal("0")
MAX_EXPORT_ROWS = 10000


@dataclass(frozen=True)
class AccountingExportResult:
    filename: str
    content: str
    row_count: int
    columns: list[str]


DEFAULT_COLUMNS = [
    "invoice_number",
    "load_number",
    "broker_customer",
    "factoring_company",
    "gross_amount",
    "funded_amount",
    "reserve_amount",
    "reserve_released_amount",
    "fee_amount",
    "deduction_amount",
    "partial_payment_amount",
    "payment_status",
    "reconciliation_status",
    "invoice_date",
    "delivery_date",
    "paid_date",
    "reconciliation_balance",
    "accounting_category",
    "revenue_category",
    "factoring_category",
    "settlement_category",
    "payment_category",
    "notes",
]

KIND_COLUMNS: dict[str, list[str]] = {
    "invoices": DEFAULT_COLUMNS,
    "factoring": DEFAULT_COLUMNS,
    "settlements": DEFAULT_COLUMNS,
    "payments": DEFAULT_COLUMNS,
    "aging": DEFAULT_COLUMNS + ["aging_days", "aging_bucket"],
}


class AccountingExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quickbooks = QuickBooksIntegrationService()

    def get_or_create_mapping(self, org_id: str) -> AccountingExportMapping:
        org_uuid = uuid.UUID(str(org_id))
        mapping = self.db.scalar(
            select(AccountingExportMapping).where(
                AccountingExportMapping.organization_id == org_uuid
            )
        )
        if mapping is None:
            mapping = AccountingExportMapping(organization_id=org_uuid)
            self.db.add(mapping)
            self.db.flush()
        return mapping

    def update_mapping(self, org_id: str, values: dict[str, str | None]) -> AccountingExportMapping:
        mapping = self.get_or_create_mapping(org_id)
        for field in (
            "accounting_category",
            "revenue_category",
            "factoring_category",
            "settlement_category",
            "payment_category",
        ):
            if field in values and values[field] is not None:
                normalized = str(values[field]).strip()
                if normalized:
                    setattr(mapping, field, normalized[:120])
        self.db.flush()
        return mapping

    def get_or_create_integration_settings(self, org_id: str) -> AccountingIntegrationSettings:
        org_uuid = uuid.UUID(str(org_id))
        settings = self.db.scalar(
            select(AccountingIntegrationSettings).where(
                AccountingIntegrationSettings.organization_id == org_uuid
            )
        )
        if settings is None:
            settings = AccountingIntegrationSettings(
                organization_id=org_uuid,
                provider="quickbooks",
                enabled=False,
                default_export_format="csv",
                sync_mode="export_ready",
                last_export_note=(
                    "CSV exports are production-ready. Direct QuickBooks sync "
                    "awaits safe OAuth configuration."
                ),
            )
            self.db.add(settings)
            self.db.flush()
        return settings

    def update_integration_settings(
        self,
        org_id: str,
        values: dict[str, object],
    ) -> AccountingIntegrationSettings:
        settings = self.get_or_create_integration_settings(org_id)
        if "enabled" in values and values["enabled"] is not None:
            settings.enabled = bool(values["enabled"])
        if "realm_id" in values:
            realm_id = values["realm_id"]
            settings.realm_id = str(realm_id).strip()[:120] if realm_id else None
        if "last_export_note" in values:
            note = values["last_export_note"]
            settings.last_export_note = str(note).strip() if note else None
        settings.provider = "quickbooks"
        settings.default_export_format = "csv"
        settings.sync_mode = "export_ready"
        self.db.flush()
        return settings

    def settings_payload(self, org_id: str) -> dict[str, object]:
        mapping = self.get_or_create_mapping(org_id)
        settings = self.get_or_create_integration_settings(org_id)
        return {
            "mapping": self.serialize_mapping(mapping),
            "quickbooks": self.serialize_integration_settings(settings),
            "quickbooks_capabilities": self.quickbooks.capability_summary(),
        }

    def build_csv_export(
        self,
        org_id: str,
        kind: AccountingExportKind,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        reconciliation_status: str | None = None,
    ) -> AccountingExportResult:
        columns = KIND_COLUMNS[kind]
        mapping = self.get_or_create_mapping(org_id)
        rows: list[dict[str, str]] = []
        for row in self._base_rows(org_id, mapping, max_source_rows=MAX_EXPORT_ROWS + 1):
            if self._include_row(
                row,
                kind=kind,
                date_from=date_from,
                date_to=date_to,
                status=status,
                reconciliation_status=reconciliation_status,
            ):
                rows.append(row)
                if len(rows) > MAX_EXPORT_ROWS:
                    break
        quota_decision = OrganizationQuotaService(self.db).can_generate_export(
            organization_id=org_id,
            estimated_rows=len(rows),
            max_rows=MAX_EXPORT_ROWS,
            enforce=True,
        )
        if not quota_decision.allowed:
            raise ValidationError(
                "Export is too large for a synchronous CSV download",
                details=quota_decision.as_dict(),
            )
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return AccountingExportResult(
            filename=f"accounting-{kind}-{stamp}.csv",
            content=output.getvalue(),
            row_count=len(rows),
            columns=columns,
        )

    def preview_rows(
        self,
        org_id: str,
        kind: AccountingExportKind,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        mapping = self.get_or_create_mapping(org_id)
        safe_limit = max(1, min(int(limit), 100))
        return list(self._base_rows(org_id, mapping, max_source_rows=safe_limit))[:safe_limit]

    def serialize_mapping(self, mapping: AccountingExportMapping) -> dict[str, str]:
        return {
            "accounting_category": mapping.accounting_category,
            "revenue_category": mapping.revenue_category,
            "factoring_category": mapping.factoring_category,
            "settlement_category": mapping.settlement_category,
            "payment_category": mapping.payment_category,
        }

    def serialize_integration_settings(
        self,
        settings: AccountingIntegrationSettings,
    ) -> dict[str, object]:
        return {
            "provider": settings.provider,
            "enabled": settings.enabled,
            "realm_id": settings.realm_id,
            "default_export_format": settings.default_export_format,
            "sync_mode": settings.sync_mode,
            "last_export_note": settings.last_export_note,
        }

    def _base_rows(
        self,
        org_id: str,
        mapping: AccountingExportMapping,
        *,
        max_source_rows: int | None = None,
    ) -> Iterable[dict[str, str]]:
        stmt = (
            select(LoadPaymentRecord)
            .join(Load, LoadPaymentRecord.load_id == Load.id)
            .where(LoadPaymentRecord.organization_id == uuid.UUID(str(org_id)))
            .options(
                selectinload(LoadPaymentRecord.load).selectinload(Load.broker),
                selectinload(LoadPaymentRecord.factoring_company),
            )
            .order_by(
                Load.delivery_date.desc().nullslast(),
                LoadPaymentRecord.updated_at.desc(),
            )
        )
        if max_source_rows is not None:
            stmt = stmt.limit(max_source_rows)
        records = self.db.scalars(stmt).unique().all()
        now = datetime.now(timezone.utc).date()
        for record in records:
            load = record.load
            expected = self._decimal(
                record.expected_amount
                or record.gross_amount
                or getattr(load, "gross_amount", None)
            )
            received = self._decimal(record.amount_received)
            reserve = self._decimal(record.reserve_amount)
            reserve_released = self._decimal(record.reserve_paid_amount)
            funded = self._decimal(record.advance_amount)
            fees = self._decimal(record.factoring_fee_amount)
            deductions = self._decimal(record.deduction_amount) + self._decimal(
                record.short_paid_amount
            )
            partial = received if received > ZERO and received < expected else ZERO
            reconciliation_balance = max(expected - received - reserve_released, ZERO)
            reference_date = record.paid_date.date() if record.paid_date else load.delivery_date
            aging_days = max((now - reference_date).days, 0) if reference_date else 0
            broker_customer = (
                getattr(getattr(load, "broker", None), "name", None)
                or load.broker_name_raw
                or ""
            )
            factoring_company = (
                getattr(getattr(record, "factoring_company", None), "company_name", None)
                or record.factor_name
                or ""
            )
            notes = "; ".join(
                part
                for part in [record.notes, record.factoring_notes, record.dispute_reason]
                if part
            )
            yield {
                "invoice_number": load.invoice_number or "",
                "load_number": load.load_number or "",
                "broker_customer": broker_customer,
                "factoring_company": factoring_company,
                "gross_amount": self._money(expected),
                "funded_amount": self._money(funded),
                "reserve_amount": self._money(reserve),
                "reserve_released_amount": self._money(reserve_released),
                "fee_amount": self._money(fees),
                "deduction_amount": self._money(deductions),
                "partial_payment_amount": self._money(partial),
                "payment_status": self._enum_value(record.payment_status),
                "reconciliation_status": self._enum_value(record.reconciliation_status),
                "invoice_date": self._date(load.submitted_at),
                "delivery_date": self._date(load.delivery_date),
                "paid_date": self._date(record.paid_date),
                "reconciliation_balance": self._money(reconciliation_balance),
                "accounting_category": mapping.accounting_category,
                "revenue_category": mapping.revenue_category,
                "factoring_category": mapping.factoring_category if record.factoring_used else "",
                "settlement_category": mapping.settlement_category,
                "payment_category": mapping.payment_category,
                "notes": notes,
                "aging_days": str(aging_days),
                "aging_bucket": self._aging_bucket(aging_days),
            }

    def _include_row(
        self,
        row: dict[str, str],
        *,
        kind: str,
        date_from: date | None,
        date_to: date | None,
        status: str | None,
        reconciliation_status: str | None,
    ) -> bool:
        if kind == "factoring" and not row["factoring_company"]:
            return False
        if (
            kind == "payments"
            and Decimal(row["funded_amount"]) <= ZERO
            and Decimal(row["partial_payment_amount"]) <= ZERO
            and not row["paid_date"]
        ):
            return False
        if status and row["payment_status"] != status:
            return False
        if reconciliation_status and row["reconciliation_status"] != reconciliation_status:
            return False
        row_date = self._parse_date(row["paid_date"] or row["delivery_date"] or row["invoice_date"])
        if date_from and row_date and row_date < date_from:
            return False
        if date_to and row_date and row_date > date_to:
            return False
        return True

    def _parse_date(self, value: str) -> date | None:
        if not value:
            return None
        return date.fromisoformat(value)

    def _decimal(self, value: Decimal | str | int | float | None) -> Decimal:
        if value is None:
            return ZERO
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _money(self, value: Decimal) -> str:
        return str(value.quantize(Decimal("0.01")))

    def _date(self, value: date | datetime | None) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.date().isoformat()
        return value.isoformat()

    def _enum_value(self, value: object) -> str:
        return str(getattr(value, "value", value) or "")

    def _aging_bucket(self, days: int) -> str:
        if days <= 30:
            return "0-30"
        if days <= 60:
            return "31-60"
        if days <= 90:
            return "61-90"
        return "90+"
