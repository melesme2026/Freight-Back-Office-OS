from __future__ import annotations

from app.domain.enums.load_status import LoadStatus
from app.services.workflow.state_machine import LoadStateMachine
from app.services.workflow.transitions import LoadTransitionApplier


class DummyLoad:
    def __init__(self) -> None:
        self.status = LoadStatus.BOOKED
        self.processing_status = "pending"
        self.submitted_at = None
        self.funded_at = None
        self.paid_at = None


def test_state_machine_allows_valid_transition() -> None:
    machine = LoadStateMachine()

    assert machine.can_transition(
        current_status=LoadStatus.BOOKED,
        new_status=LoadStatus.IN_TRANSIT,
    ) is True


def test_state_machine_blocks_invalid_transition() -> None:
    machine = LoadStateMachine()

    assert machine.can_transition(
        current_status=LoadStatus.BOOKED,
        new_status=LoadStatus.FULLY_PAID,
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


def test_transition_applier_sets_processing_completed_for_invoice_ready() -> None:
    load = DummyLoad()
    applier = LoadTransitionApplier()

    updated = applier.apply_status_change(
        load=load,
        new_status=LoadStatus.INVOICE_READY,
    )

    assert updated.status == LoadStatus.INVOICE_READY
    assert updated.processing_status == "completed"


def test_transition_applier_sets_failed_for_docs_needs_attention() -> None:
    load = DummyLoad()
    applier = LoadTransitionApplier()

    updated = applier.apply_status_change(
        load=load,
        new_status=LoadStatus.DOCS_NEEDS_ATTENTION,
    )

    assert updated.status == LoadStatus.DOCS_NEEDS_ATTENTION
    assert updated.processing_status == "failed"
