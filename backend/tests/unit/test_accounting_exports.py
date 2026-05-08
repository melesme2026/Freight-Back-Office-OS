from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO

import pytest
from app.api.v1.accounting import _authorize_accounting_read, _authorize_accounting_write
from app.core.exceptions import ForbiddenError
from app.domain.enums.factoring import FactoringReconciliationStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.services.accounting.accounting_export_service import (
    DEFAULT_COLUMNS,
    AccountingExportService,
)
from app.services.loads.load_service import LoadService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService

ORG_ID = "00000000-0000-0000-0000-000000003801"


def _make_payment_record(db_session):
    load = LoadService(db_session).create_load(
        organization_id=ORG_ID,
        customer_account_id="00000000-0000-0000-0000-000000003802",
        driver_id="00000000-0000-0000-0000-000000003803",
        load_number="LOAD-38",
        invoice_number="INV-38",
        broker_name_raw="Acme Broker",
        gross_amount=Decimal("2500.00"),
        delivery_date=datetime(2026, 5, 1, tzinfo=timezone.utc).date(),
    )
    load.submitted_at = datetime(2026, 5, 2, tzinfo=timezone.utc)
    record = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), ORG_ID)
    record.expected_amount = Decimal("2500.00")
    record.gross_amount = Decimal("2500.00")
    record.amount_received = Decimal("1800.00")
    record.advance_amount = Decimal("1700.00")
    record.reserve_amount = Decimal("500.00")
    record.reserve_paid_amount = Decimal("100.00")
    record.factoring_fee_amount = Decimal("75.00")
    record.deduction_amount = Decimal("25.00")
    record.factoring_used = True
    record.factor_name = "Reliable Factor"
    record.payment_status = LoadPaymentStatus.PARTIALLY_PAID
    record.reconciliation_status = FactoringReconciliationStatus.PARTIALLY_RECONCILED
    record.paid_date = datetime(2026, 5, 4, tzinfo=timezone.utc)
    record.notes = "partial ACH received"
    db_session.flush()
    return record


def _csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))


def test_invoice_export_csv_has_consistent_accounting_columns(db_session):
    _make_payment_record(db_session)

    result = AccountingExportService(db_session).build_csv_export(ORG_ID, "invoices")
    rows = _csv_rows(result.content)

    assert result.columns == DEFAULT_COLUMNS
    assert result.row_count == 1
    assert rows[0]["invoice_number"] == "INV-38"
    assert rows[0]["load_number"] == "LOAD-38"
    assert rows[0]["broker_customer"] == "Acme Broker"
    assert rows[0]["gross_amount"] == "2500.00"
    assert rows[0]["revenue_category"] == "Freight Revenue"


def test_settlement_export_calculates_reserve_fees_partial_payments_and_balance(db_session):
    _make_payment_record(db_session)

    result = AccountingExportService(db_session).build_csv_export(ORG_ID, "settlements")
    row = _csv_rows(result.content)[0]

    assert row["funded_amount"] == "1700.00"
    assert row["reserve_amount"] == "500.00"
    assert row["reserve_released_amount"] == "100.00"
    assert row["fee_amount"] == "75.00"
    assert row["deduction_amount"] == "25.00"
    assert row["partial_payment_amount"] == "1800.00"
    assert row["reconciliation_balance"] == "600.00"


def test_factoring_payments_and_aging_exports_filter_rows(db_session):
    _make_payment_record(db_session)
    service = AccountingExportService(db_session)

    factoring = _csv_rows(service.build_csv_export(ORG_ID, "factoring").content)
    payments = _csv_rows(
        service.build_csv_export(ORG_ID, "payments", status="partially_paid").content
    )
    aging = _csv_rows(
        service.build_csv_export(
            ORG_ID,
            "aging",
            reconciliation_status="partially_reconciled",
        ).content
    )

    assert len(factoring) == 1
    assert factoring[0]["factoring_company"] == "Reliable Factor"
    assert len(payments) == 1
    assert payments[0]["payment_status"] == "partially_paid"
    assert len(aging) == 1
    assert "aging_days" in aging[0]
    assert "aging_bucket" in aging[0]


def test_accounting_mapping_updates_are_exported(db_session):
    _make_payment_record(db_session)
    service = AccountingExportService(db_session)
    service.update_mapping(
        ORG_ID,
        {
            "accounting_category": "Ops Finance",
            "revenue_category": "Linehaul Revenue",
            "factoring_category": "Factoring Fees",
            "settlement_category": "Driver Settlements",
            "payment_category": "Broker Payments",
        },
    )

    row = _csv_rows(service.build_csv_export(ORG_ID, "invoices").content)[0]

    assert row["accounting_category"] == "Ops Finance"
    assert row["revenue_category"] == "Linehaul Revenue"
    assert row["factoring_category"] == "Factoring Fees"
    assert row["settlement_category"] == "Driver Settlements"
    assert row["payment_category"] == "Broker Payments"


def test_quickbooks_foundation_is_export_ready_not_direct_sync(db_session):
    payload = AccountingExportService(db_session).settings_payload(ORG_ID)

    assert payload["quickbooks"]["provider"] == "quickbooks"
    assert payload["quickbooks"]["sync_mode"] == "export_ready"
    assert payload["quickbooks_capabilities"]["supports_direct_push"] is False


def test_accounting_export_rbac_blocks_drivers():
    with pytest.raises(ForbiddenError):
        _authorize_accounting_read({"role": "driver"})
    with pytest.raises(ForbiddenError):
        _authorize_accounting_write({"role": "driver"})
