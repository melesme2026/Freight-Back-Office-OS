from __future__ import annotations

import pytest

from app.core.exceptions import InvalidTransitionError, ValidationError
from app.domain.enums.load_status import LoadStatus
from app.services.loads.load_service import LoadService
from app.services.documents.document_service import DocumentService
from app.services.workflow.workflow_engine import WorkflowEngine


def test_load_lifecycle_transition_from_new_to_docs_received(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000601",
        customer_account_id="00000000-0000-0000-0000-000000000602",
        driver_id="00000000-0000-0000-0000-000000000603",
        load_number="LIFE-1001",
    )

    result = workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.DOCS_RECEIVED,
    )

    refreshed = load_service.get_load(str(load.id))

    assert result["id"] == str(load.id)
    assert refreshed.status == LoadStatus.DOCS_RECEIVED


def test_load_lifecycle_can_transition_to_exception(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000611",
        customer_account_id="00000000-0000-0000-0000-000000000612",
        driver_id="00000000-0000-0000-0000-000000000613",
        load_number="LIFE-1002",
    )

    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.EXCEPTION,
    )

    refreshed = load_service.get_load(str(load.id))

    assert refreshed.status == LoadStatus.EXCEPTION
    assert str(refreshed.processing_status) == "failed"


def test_broker_factoring_workflow_requires_docs_and_no_blocking_issues(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000621",
        customer_account_id="00000000-0000-0000-0000-000000000622",
        driver_id="00000000-0000-0000-0000-000000000623",
        load_number="LIFE-1003",
    )

    with pytest.raises(InvalidTransitionError):
        workflow_engine.transition_load(
            load_id=str(load.id),
            new_status=LoadStatus.SUBMITTED_TO_BROKER,
        )

    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.DOCS_RECEIVED,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.NEEDS_REVIEW,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.READY_TO_SUBMIT,
    )

    with pytest.raises(ValidationError):
        workflow_engine.transition_load(
            load_id=str(load.id),
            new_status=LoadStatus.SUBMITTED_TO_BROKER,
        )

    document_service = DocumentService(db_session)
    for index, document_type in enumerate(["rate_confirmation", "proof_of_delivery", "invoice"], start=1):
        document_service.create_document(
            organization_id="00000000-0000-0000-0000-000000000631",
            customer_account_id="00000000-0000-0000-0000-000000000632",
            storage_key=f"uploads/lifecycle-actions-{index}.pdf",
            source_channel="manual",
            load_id=str(load.id),
            document_type=document_type,
            original_filename=f"lifecycle-actions-{index}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1100 + index,
        )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.SUBMITTED_TO_BROKER,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.WAITING_ON_BROKER,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.SUBMITTED_TO_FACTORING,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.WAITING_ON_FUNDING,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.FUNDED,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.PAID,
    )

    refreshed = load_service.get_load(str(load.id))
    assert refreshed.status == LoadStatus.PAID


def test_operational_actions_publish_required_events(db_session) -> None:
    load_service = LoadService(db_session)
    workflow_engine = WorkflowEngine(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000631",
        customer_account_id="00000000-0000-0000-0000-000000000632",
        driver_id="00000000-0000-0000-0000-000000000633",
        load_number="LIFE-1004",
    )
    document_service = DocumentService(db_session)
    for index, document_type in enumerate(["rate_confirmation", "proof_of_delivery", "invoice"], start=1):
        document_service.create_document(
            organization_id="00000000-0000-0000-0000-000000000621",
            customer_account_id="00000000-0000-0000-0000-000000000622",
            storage_key=f"uploads/lifecycle-required-{index}.pdf",
            source_channel="manual",
            load_id=str(load.id),
            document_type=document_type,
            original_filename=f"lifecycle-required-{index}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1100 + index,
        )

    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.DOCS_RECEIVED,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.NEEDS_REVIEW,
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.READY_TO_SUBMIT,
    )

    workflow_engine.apply_operational_action(
        load_id=str(load.id),
        action="mark_sent_to_broker",
    )
    workflow_engine.apply_operational_action(
        load_id=str(load.id),
        action="mark_waiting_on_broker",
    )
    workflow_engine.apply_operational_action(
        load_id=str(load.id),
        action="mark_submitted_to_factoring",
    )
    workflow_engine.transition_load(
        load_id=str(load.id),
        new_status=LoadStatus.WAITING_ON_FUNDING,
    )
    workflow_engine.apply_operational_action(
        load_id=str(load.id),
        action="mark_funded",
    )

    refreshed = load_service.get_load(str(load.id))
    event_types = {event.event_type for event in refreshed.workflow_events}

    assert "broker_contacted" in event_types
    assert "broker_response_received" in event_types
    assert "submitted_to_factoring" in event_types
    assert "funding_confirmed" in event_types
