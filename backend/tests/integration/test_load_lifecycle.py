from __future__ import annotations

import pytest

from app.core.exceptions import InvalidTransitionError, ValidationError
from app.domain.enums.load_status import LoadStatus
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService
from app.services.workflow.workflow_engine import WorkflowEngine


def _seed_submission_docs(db_session, load_id: str) -> None:
    document_service = DocumentService(db_session)
    for index, document_type in enumerate(["rate_confirmation", "proof_of_delivery", "invoice"], start=1):
        document_service.create_document(
            organization_id="00000000-0000-0000-0000-000000000631",
            customer_account_id="00000000-0000-0000-0000-000000000632",
            storage_key=f"uploads/lifecycle-{index}.pdf",
            source_channel="manual",
            load_id=load_id,
            document_type=document_type,
            original_filename=f"lifecycle-{index}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1100 + index,
        )


def test_load_lifecycle_core_transitions(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000601",
        customer_account_id="00000000-0000-0000-0000-000000000602",
        driver_id="00000000-0000-0000-0000-000000000603",
        load_number="LIFE-2001",
    )

    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.IN_TRANSIT)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DELIVERED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DOCS_RECEIVED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.INVOICE_READY)

    refreshed = load_service.get_load(str(load.id))
    assert refreshed.status == LoadStatus.INVOICE_READY


def test_submission_requires_invoice_ready_and_docs(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000621",
        customer_account_id="00000000-0000-0000-0000-000000000622",
        driver_id="00000000-0000-0000-0000-000000000623",
        load_number="LIFE-2002",
    )

    with pytest.raises(InvalidTransitionError):
        workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.SUBMITTED_TO_BROKER)

    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.IN_TRANSIT)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DELIVERED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DOCS_RECEIVED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.INVOICE_READY)

    with pytest.raises(ValidationError):
        workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.SUBMITTED_TO_BROKER)

    _seed_submission_docs(db_session, str(load.id))
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.SUBMITTED_TO_BROKER)

    refreshed = load_service.get_load(str(load.id))
    assert refreshed.status == LoadStatus.SUBMITTED_TO_BROKER


def test_factoring_rejection_resubmission_and_payment_flow(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000641",
        customer_account_id="00000000-0000-0000-0000-000000000642",
        driver_id="00000000-0000-0000-0000-000000000643",
        load_number="LIFE-2003",
    )

    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.IN_TRANSIT)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DELIVERED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.DOCS_RECEIVED)
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.INVOICE_READY)
    _seed_submission_docs(db_session, str(load.id))

    workflow_engine.apply_operational_action(load_id=str(load.id), action="submit_to_factoring")
    workflow_engine.apply_operational_action(load_id=str(load.id), action="mark_packet_rejected")
    workflow_engine.apply_operational_action(load_id=str(load.id), action="mark_resubmission_needed")
    workflow_engine.transition_load(load_id=str(load.id), new_status=LoadStatus.INVOICE_READY)
    workflow_engine.apply_operational_action(load_id=str(load.id), action="submit_to_factoring")
    workflow_engine.apply_operational_action(load_id=str(load.id), action="mark_advance_paid")
    workflow_engine.apply_operational_action(load_id=str(load.id), action="mark_reserve_pending")
    workflow_engine.apply_operational_action(load_id=str(load.id), action="mark_fully_paid")

    refreshed = load_service.get_load(str(load.id))
    assert refreshed.status == LoadStatus.FULLY_PAID
    assert refreshed.submitted_at is not None
    assert refreshed.funded_at is not None
    assert refreshed.paid_at is not None
