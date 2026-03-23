from __future__ import annotations

from app.domain.enums.load_status import LoadStatus
from app.services.loads.load_service import LoadService
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