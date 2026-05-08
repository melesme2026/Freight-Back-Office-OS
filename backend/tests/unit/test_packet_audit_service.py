from __future__ import annotations

# ruff: noqa: E501
from decimal import Decimal

from app.domain.enums.document_type import DocumentType
from app.domain.models.extracted_field import ExtractedField
from app.domain.models.submission_event import SubmissionEvent
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService
from app.services.loads.submission_packet_service import SubmissionPacketService
from app.services.packet_intelligence.packet_audit_service import PacketAuditService

CUSTOMER_ID = "00000000-0000-0000-0000-000000009902"
DRIVER_ID = "00000000-0000-0000-0000-000000009903"
STAFF_ID = "00000000-0000-0000-0000-000000009999"


def _create_load(db_session, *, org_id: str, invoice_number: str = "INV-37", gross_amount: str = "1000.00", notes: str | None = None):
    return LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=CUSTOMER_ID,
        driver_id=DRIVER_ID,
        load_number=f"LD-{org_id[-4:]}",
        invoice_number=invoice_number,
        gross_amount=gross_amount,
        notes=notes,
        rate_confirmation_number="BR-123",
    )


def _add_doc(db_session, *, org_id: str, load, doc_type: DocumentType):
    return DocumentService(db_session).create_document(
        organization_id=org_id,
        customer_account_id=CUSTOMER_ID,
        driver_id=DRIVER_ID,
        load_id=str(load.id),
        source_channel="manual",
        document_type=doc_type,
        storage_key=f"uploads/{load.id}-{doc_type.value}.pdf",
        original_filename=f"{doc_type.value}.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
    )


def _add_field(db_session, *, org_id: str, load, document, name: str, text: str | None = None, number: str | None = None):
    field = ExtractedField(
        organization_id=org_id,
        document_id=document.id,
        load_id=load.id,
        field_name=name,
        field_value_text=text,
        field_value_number=Decimal(number) if number is not None else None,
        confidence_score=Decimal("0.9500"),
        source_engine="test",
    )
    db_session.add(field)
    db_session.flush()
    return field


def _seed_complete_packet(db_session, *, org_id: str, invoice_number: str = "INV-37", gross_amount: str = "1000.00"):
    load = _create_load(db_session, org_id=org_id, invoice_number=invoice_number, gross_amount=gross_amount)
    invoice = _add_doc(db_session, org_id=org_id, load=load, doc_type=DocumentType.INVOICE)
    ratecon = _add_doc(db_session, org_id=org_id, load=load, doc_type=DocumentType.RATE_CONFIRMATION)
    pod = _add_doc(db_session, org_id=org_id, load=load, doc_type=DocumentType.PROOF_OF_DELIVERY)
    _add_doc(db_session, org_id=org_id, load=load, doc_type=DocumentType.BILL_OF_LADING)
    _add_field(db_session, org_id=org_id, load=load, document=invoice, name="invoice_amount", number=gross_amount)
    _add_field(db_session, org_id=org_id, load=load, document=invoice, name="broker_reference", text="BR-123")
    _add_field(db_session, org_id=org_id, load=load, document=ratecon, name="rate_confirmation_number", text="BR-123")
    _add_field(db_session, org_id=org_id, load=load, document=pod, name="signature_present", text="yes")
    packet = SubmissionPacketService(db_session).create_packet_from_load(str(load.id), org_id, STAFF_ID)
    return load, packet, invoice, ratecon, pod


def test_packet_audit_detects_missing_documents_and_blocking_severity(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037001"
    load = _create_load(db_session, org_id=org_id)
    _add_doc(db_session, org_id=org_id, load=load, doc_type=DocumentType.INVOICE)

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id)

    codes = {finding.code for finding in result.findings}
    assert "missing_pod" in codes
    assert "missing_rate_confirmation" in codes
    assert result.status == "failed"
    assert any(finding.severity == "blocking" for finding in result.findings)


def test_packet_audit_detects_duplicate_invoice_number(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037002"
    _create_load(db_session, org_id=org_id, invoice_number="DUP-1")
    load, _packet, _invoice, _ratecon, _pod = _seed_complete_packet(db_session, org_id=org_id, invoice_number="DUP-1")

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id)

    duplicate = [finding for finding in result.findings if finding.code == "duplicate_invoice_number"]
    assert duplicate
    assert duplicate[0].severity == "blocking"
    assert result.status == "failed"


def test_packet_audit_detects_amount_mismatch(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037003"
    load, _packet, invoice, _ratecon, _pod = _seed_complete_packet(db_session, org_id=org_id, gross_amount="1000.00")
    for field in invoice.extracted_fields:
        if field.field_name == "invoice_amount":
            field.field_value_number = Decimal("900.00")

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id)

    assert any(finding.code == "amount_mismatch" and finding.severity == "warning" for finding in result.findings)
    assert result.status == "warning"


def test_packet_audit_detects_broker_reference_mismatch(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037004"
    load, _packet, invoice, _ratecon, _pod = _seed_complete_packet(db_session, org_id=org_id)
    for field in invoice.extracted_fields:
        if field.field_name == "broker_reference":
            field.field_value_text = "WRONG-REF"

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id)

    assert any(finding.code == "broker_reference_mismatch" for finding in result.findings)
    assert result.status == "warning"


def test_packet_audit_confidence_scoring_passes_complete_packet(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037005"
    load, _packet, _invoice, _ratecon, _pod = _seed_complete_packet(db_session, org_id=org_id)
    load.extraction_confidence_avg = Decimal("0.9500")

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id)

    assert result.status == "passed"
    assert result.confidence_score == 100
    assert result.findings == []


def test_packet_audit_detects_repeated_packet_send_attempt(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000037006"
    load, packet, _invoice, _ratecon, _pod = _seed_complete_packet(db_session, org_id=org_id)
    db_session.add(
        SubmissionEvent(
            organization_id=org_id,
            load_id=load.id,
            submission_packet_id=packet.id,
            event_type="packet_email_sent",
            message="Packet email sent.",
        )
    )
    db_session.flush()

    result = PacketAuditService(db_session).audit_load(load_id=str(load.id), org_id=org_id, packet_id=str(packet.id))

    assert any(finding.code == "repeated_packet_send" and finding.severity == "warning" for finding in result.findings)
