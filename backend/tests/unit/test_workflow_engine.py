from __future__ import annotations

from app.domain.enums.load_status import LoadStatus
from app.services.workflow.state_machine import LoadStateMachine
from app.services.workflow.transitions import LoadTransitionApplier


class DummyLoad:
    def __init__(self) -> None:
        self.status = LoadStatus.NEW
        self.processing_status = "pending"
        self.submitted_at = None
        self.funded_at = None
        self.paid_at = None


def test_state_machine_allows_valid_transition() -> None:
    machine = LoadStateMachine()

    assert machine.can_transition(
        current_status=LoadStatus.NEW,
        new_status=LoadStatus.DOCS_RECEIVED,
    ) is True


def test_state_machine_blocks_invalid_transition() -> None:
    machine = LoadStateMachine()

    assert machine.can_transition(
        current_status=LoadStatus.NEW,
        new_status=LoadStatus.PAID,
    ) is False


def test_transition_applier_sets_submitted_timestamp() -> None:
    load = DummyLoad()
    applier = LoadTransitionApplier()

    updated = applier.apply_status_change(
        load=load,
        new_status=LoadStatus.SUBMITTED_TO_BROKER,
    )

    assert updated.status == LoadStatus.SUBMITTED_TO_BROKER
    assert updated.submitted_at is not None


def test_transition_applier_sets_processing_completed_for_ready_to_submit() -> None:
    load = DummyLoad()
    applier = LoadTransitionApplier()

    updated = applier.apply_status_change(
        load=load,
        new_status=LoadStatus.READY_TO_SUBMIT,
    )

    assert updated.status == LoadStatus.READY_TO_SUBMIT
    assert updated.processing_status == "completed"


def test_transition_applier_sets_failed_for_exception() -> None:
    load = DummyLoad()
    applier = LoadTransitionApplier()

    updated = applier.apply_status_change(
        load=load,
        new_status=LoadStatus.EXCEPTION,
    )

    assert updated.status == LoadStatus.EXCEPTION
    assert updated.processing_status == "failed"
