from __future__ import annotations

from app.core.exceptions import InvalidTransitionError
from app.domain.enums.load_status import LoadStatus


class LoadStateMachine:
    ALLOWED_TRANSITIONS: dict[LoadStatus, set[LoadStatus]] = {
        LoadStatus.BOOKED: {
            LoadStatus.IN_TRANSIT,
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.IN_TRANSIT: {
            LoadStatus.DELIVERED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.DELIVERED: {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.DOCS_RECEIVED: {
            LoadStatus.INVOICE_READY,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.DOCS_NEEDS_ATTENTION: {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.INVOICE_READY,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.INVOICE_READY: {
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.SUBMITTED_TO_BROKER: {
            LoadStatus.FULLY_PAID,
            LoadStatus.SHORT_PAID,
            LoadStatus.DISPUTED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.SUBMITTED_TO_FACTORING: {
            LoadStatus.PACKET_REJECTED,
            LoadStatus.ADVANCE_PAID,
            LoadStatus.DISPUTED,
            LoadStatus.SHORT_PAID,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.PACKET_REJECTED: {
            LoadStatus.RESUBMISSION_NEEDED,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.RESUBMISSION_NEEDED: {
            LoadStatus.INVOICE_READY,
            LoadStatus.SUBMITTED_TO_FACTORING,
            LoadStatus.DOCS_NEEDS_ATTENTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.ADVANCE_PAID: {
            LoadStatus.RESERVE_PENDING,
            LoadStatus.FULLY_PAID,
            LoadStatus.SHORT_PAID,
            LoadStatus.DISPUTED,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.RESERVE_PENDING: {
            LoadStatus.FULLY_PAID,
            LoadStatus.SHORT_PAID,
            LoadStatus.DISPUTED,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.SHORT_PAID: {
            LoadStatus.DISPUTED,
            LoadStatus.FULLY_PAID,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.DISPUTED: {
            LoadStatus.RESUBMISSION_NEEDED,
            LoadStatus.RESERVE_PENDING,
            LoadStatus.SHORT_PAID,
            LoadStatus.FULLY_PAID,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.FULLY_PAID: {LoadStatus.ARCHIVED},
        LoadStatus.ARCHIVED: set(),
    }

    def can_transition(
        self,
        *,
        current_status: LoadStatus,
        new_status: LoadStatus,
    ) -> bool:
        if current_status == new_status:
            return True

        return new_status in self.ALLOWED_TRANSITIONS.get(current_status, set())

    def assert_transition_allowed(
        self,
        *,
        current_status: LoadStatus,
        new_status: LoadStatus,
    ) -> None:
        if not self.can_transition(current_status=current_status, new_status=new_status):
            raise InvalidTransitionError(
                f"Cannot transition load from {current_status} to {new_status}",
                details={
                    "current_status": str(current_status),
                    "new_status": str(new_status),
                    "allowed_transitions": sorted(
                        str(status)
                        for status in self.ALLOWED_TRANSITIONS.get(current_status, set())
                    ),
                },
            )
