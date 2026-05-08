from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest

from app.api.v1.operations import _require_command_center_access
from app.core.exceptions import ForbiddenError
from app.domain.enums.document_type import DocumentType
from app.domain.enums.factoring import FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.broker import Broker
from app.domain.models.driver import Driver
from app.domain.models.load_document import LoadDocument
from app.domain.models.submission_packet import SubmissionPacket
from app.domain.models.validation_issue import ValidationIssue
from app.services.loads.load_service import LoadService
from app.services.operations.command_center_service import DispatcherCommandCenterService
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService

ORG_ID = "00000000-0000-0000-0000-000000043001"
OTHER_ORG_ID = "00000000-0000-0000-0000-000000043002"
CUSTOMER_ID = "00000000-0000-0000-0000-000000043101"
DRIVER_ID = "00000000-0000-0000-0000-000000043201"
BROKER_ID = "00000000-0000-0000-0000-000000043301"


def _seed_parties(db_session, org_id: str = ORG_ID) -> None:
    db_session.add_all(
        [
            Driver(id=uuid.UUID(DRIVER_ID), organization_id=org_id, customer_account_id=CUSTOMER_ID, full_name="Command Driver", phone="555-4301"),
            Broker(id=uuid.UUID(BROKER_ID), organization_id=org_id, name="Command Broker", mc_number="MC43"),
        ]
    )
    db_session.flush()


def _make_load(db_session, *, load_number: str, org_id: str = ORG_ID, status: LoadStatus = LoadStatus.DELIVERED, delivery_days_ago: int = 5):
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=CUSTOMER_ID,
        driver_id=DRIVER_ID,
        broker_id=BROKER_ID,
        load_number=load_number,
        invoice_number=f"INV-{load_number}",
        gross_amount=Decimal("2500.00"),
        pickup_location="Dallas, TX",
        delivery_location="Atlanta, GA",
        delivery_date=datetime.now(timezone.utc).date() - timedelta(days=delivery_days_ago),
    )
    load.status = status
    db_session.flush()
    return load


def _add_document(db_session, load, document_type: DocumentType) -> None:
    db_session.add(
        LoadDocument(
            organization_id=load.organization_id,
            customer_account_id=load.customer_account_id,
            driver_id=load.driver_id,
            load_id=load.id,
            document_type=document_type,
            original_filename=f"{document_type.value}.pdf",
            storage_key=f"command-center/{load.id}/{document_type.value}.pdf",
            file_hash_sha256=f"{str(load.id).replace('-', '')[:24]}{document_type.value[:8]}",
            received_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()
    db_session.expire_all()


def _payment(db_session, load, *, expected: str = "2500", received: str = "0", status: LoadPaymentStatus = LoadPaymentStatus.AWAITING_PAYMENT):
    record = PaymentReconciliationService(db_session).get_or_create_for_load(str(load.id), str(load.organization_id))
    record.expected_amount = Decimal(expected)
    record.amount_received = Decimal(received)
    record.payment_status = status
    record.factoring_status = FactoringWorkflowStatus.NOT_FACTORED
    record.reconciliation_status = FactoringReconciliationStatus.UNRECONCILED
    return record


def test_command_center_generates_alerts_tasks_missing_docs_and_collections(db_session):
    _seed_parties(db_session)
    missing_pod = _make_load(db_session, load_number="CMD-MISSING-POD", delivery_days_ago=12)
    _add_document(db_session, missing_pod, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, missing_pod, DocumentType.INVOICE)
    db_session.add(
        SubmissionPacket(
            organization_id=ORG_ID,
            load_id=missing_pod.id,
            packet_reference="PKT-43",
            status="blocked",
        )
    )
    db_session.add(
        ValidationIssue(
            organization_id=ORG_ID,
            load_id=missing_pod.id,
            rule_code="missing_signature",
            severity=ValidationSeverity.CRITICAL,
            title="POD signature missing",
            description="POD cannot be accepted without signature.",
            is_blocking=True,
            is_resolved=False,
        )
    )

    overdue = _make_load(db_session, load_number="CMD-OVERDUE", delivery_days_ago=65)
    _add_document(db_session, overdue, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, overdue, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, overdue, DocumentType.INVOICE)
    record = _payment(db_session, overdue, expected="6000", received="0", status=LoadPaymentStatus.DISPUTED)
    record.factoring_status = FactoringWorkflowStatus.RESERVE_PENDING
    record.reserve_amount = Decimal("500")
    record.reserve_paid_amount = Decimal("0")

    data = DispatcherCommandCenterService(db_session).get_command_center(org_id=ORG_ID)

    assert data["kpis"]["active_loads"] == 2
    assert data["kpis"]["loads_missing_docs"] == 1
    assert data["kpis"]["overdue_invoices"] == 1
    assert data["kpis"]["unresolved_packet_intelligence_blockers"] == 1
    assert data["kpis"]["factoring_reserve_pending"] == 1
    assert data["collections"]["summary"]["unpaid_total"] == "6000.00"

    alert_types = {alert["type"] for alert in data["alerts"]}
    assert {"missing_pod", "blocked_packet_send", "invoice_overdue", "factoring_issue", "packet_intelligence_blocker"}.issubset(alert_types)
    assert any(task["type"] == "missing_document" and task["severity"] == "critical" for task in data["tasks"]["items"])
    assert any(task["type"] == "follow_up_overdue_invoice" for task in data["tasks"]["items"])
    assert data["priority_cards"][0]["key"] == "critical_alerts"


def test_command_center_is_org_scoped(db_session):
    _seed_parties(db_session)
    org_load = _make_load(db_session, load_number="CMD-ORG")
    _payment(db_session, org_load, expected="1000", received="0")

    other_load = _make_load(db_session, load_number="CMD-OTHER", org_id=OTHER_ORG_ID)
    _payment(db_session, other_load, expected="9000", received="0")

    data = DispatcherCommandCenterService(db_session).get_command_center(org_id=ORG_ID)

    assert data["kpis"]["active_loads"] == 1
    assert data["collections"]["summary"]["unpaid_total"] == "1000.00"
    assert all(item["load_number"] != "CMD-OTHER" for item in data["collections"]["items"])


def test_command_center_prioritizes_blocked_packets_and_overdue_collections(db_session):
    _seed_parties(db_session)
    blocked = _make_load(db_session, load_number="CMD-BLOCKED", status=LoadStatus.PACKET_REJECTED, delivery_days_ago=2)
    db_session.add(SubmissionPacket(organization_id=ORG_ID, load_id=blocked.id, packet_reference="PKT-BLOCKED", status="failed"))

    mild = _make_load(db_session, load_number="CMD-MILD", status=LoadStatus.BOOKED, delivery_days_ago=1)
    _add_document(db_session, mild, DocumentType.RATE_CONFIRMATION)

    overdue = _make_load(db_session, load_number="CMD-AGED", delivery_days_ago=90)
    _add_document(db_session, overdue, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, overdue, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, overdue, DocumentType.INVOICE)
    _payment(db_session, overdue, expected="7000", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)

    data = DispatcherCommandCenterService(db_session).get_command_center(org_id=ORG_ID)

    assert data["missing_docs"]["items"][0]["load_number"] == "CMD-BLOCKED"
    assert data["collections"]["items"][0]["load_number"] == "CMD-AGED"
    assert data["collections"]["items"][0]["severity"] == "critical"


def test_driver_blocked_from_command_center_authorizer():
    with pytest.raises(ForbiddenError):
        _require_command_center_access({"role": "driver"})


def test_ai_operations_assistant_explains_invoice_risk_broker_behavior_and_collections(db_session):
    _seed_parties(db_session)
    missing_pod = _make_load(db_session, load_number="AI-MISSING-POD", delivery_days_ago=8)
    _add_document(db_session, missing_pod, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, missing_pod, DocumentType.INVOICE)

    old_invoice = _make_load(db_session, load_number="AI-OLD", delivery_days_ago=70)
    _add_document(db_session, old_invoice, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, old_invoice, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, old_invoice, DocumentType.INVOICE)
    old_record = _payment(db_session, old_invoice, expected="8200", received="0", status=LoadPaymentStatus.AWAITING_PAYMENT)

    disputed = _make_load(db_session, load_number="AI-DISPUTED", delivery_days_ago=50)
    _add_document(db_session, disputed, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, disputed, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, disputed, DocumentType.INVOICE)
    disputed_record = _payment(db_session, disputed, expected="3000", received="500", status=LoadPaymentStatus.DISPUTED)
    disputed_record.reconciliation_status = FactoringReconciliationStatus.PARTIALLY_RECONCILED
    disputed_record.factoring_status = FactoringWorkflowStatus.RESERVE_PENDING
    disputed_record.reserve_amount = Decimal("750")
    disputed_record.reserve_paid_amount = Decimal("0")

    paid = _make_load(db_session, load_number="AI-PAID", delivery_days_ago=95)
    _add_document(db_session, paid, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, paid, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, paid, DocumentType.INVOICE)
    paid_record = _payment(db_session, paid, expected="2000", received="2000", status=LoadPaymentStatus.PAID)
    paid_record.reconciliation_status = FactoringReconciliationStatus.RECONCILED
    paid_record.paid_date = datetime.now(timezone.utc) - timedelta(days=20)

    data = DispatcherCommandCenterService(db_session).get_command_center(org_id=ORG_ID)
    assistant = data["ai_operations_assistant"]

    assert assistant["explainability"]["mode"] == "deterministic_rules_only"
    assert assistant["explainability"]["uses_llm"] is False
    assert assistant["explainability"]["autonomous_actions"] is False
    assert any("missing POD" in item["title"] for item in assistant["summary"])
    assert any("over 45 days overdue" in item["title"] for item in assistant["summary"])

    risk_by_load = {item["load_number"]: item for item in assistant["invoice_risks"]}
    assert risk_by_load["AI-OLD"]["risk_level"] == "critical"
    assert any("more than 60 days" in reason for reason in risk_by_load["AI-OLD"]["risk_reasons"])
    assert risk_by_load["AI-DISPUTED"]["risk_level"] in {"high", "critical"}
    assert any("Payment status is disputed" in reason for reason in risk_by_load["AI-DISPUTED"]["risk_reasons"])

    collections = assistant["collections_priorities"]
    assert collections[0]["priority_score"] >= collections[1]["priority_score"]
    assert {collections[0]["load_number"], collections[1]["load_number"]} == {"AI-OLD", "AI-DISPUTED"}
    assert collections[0]["collection_rank_reason"]
    assert any(item["recommended_action"] for item in collections)

    broker = assistant["broker_insights"][0]
    assert broker["broker_name"] == "Command Broker"
    assert broker["unpaid_invoice_count"] == 2
    assert broker["dispute_or_short_paid_count"] == 1
    assert broker["contributing_factors"]

    recommendations = assistant["recommendations"]
    assert recommendations
    assert all(item["autonomous_action"] is False for item in recommendations)
    assert all(item["contributing_factors"] for item in recommendations)


def test_ai_operations_assistant_remains_org_scoped(db_session):
    _seed_parties(db_session)
    org_load = _make_load(db_session, load_number="AI-ORG", delivery_days_ago=61)
    _add_document(db_session, org_load, DocumentType.RATE_CONFIRMATION)
    _add_document(db_session, org_load, DocumentType.PROOF_OF_DELIVERY)
    _add_document(db_session, org_load, DocumentType.INVOICE)
    _payment(db_session, org_load, expected="1000", received="0")

    other_load = _make_load(db_session, load_number="AI-OTHER", org_id=OTHER_ORG_ID, delivery_days_ago=90)
    _payment(db_session, other_load, expected="9000", received="0", status=LoadPaymentStatus.DISPUTED)

    data = DispatcherCommandCenterService(db_session).get_command_center(org_id=ORG_ID)
    assistant = data["ai_operations_assistant"]

    serialized = str(assistant)
    assert "AI-ORG" in serialized
    assert "AI-OTHER" not in serialized
    assert "9000.00" not in serialized
