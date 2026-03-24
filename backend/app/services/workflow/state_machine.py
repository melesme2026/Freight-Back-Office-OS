from __future__ import annotations

from app.core.exceptions import InvalidTransitionError
from app.domain.enums.load_status import LoadStatus


class LoadStateMachine:
    ALLOWED_TRANSITIONS: dict[LoadStatus, set[LoadStatus]] = {
        LoadStatus.NEW: {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.EXTRACTING,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.DOCS_RECEIVED: {
            LoadStatus.EXTRACTING,
            LoadStatus.NEEDS_REVIEW,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.EXTRACTING: {
            LoadStatus.NEEDS_REVIEW,
            LoadStatus.VALIDATED,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.NEEDS_REVIEW: {
            LoadStatus.VALIDATED,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.VALIDATED: {
            LoadStatus.READY_TO_SUBMIT,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.READY_TO_SUBMIT: {
            LoadStatus.SUBMITTED,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.SUBMITTED: {
            LoadStatus.FUNDED,
            LoadStatus.PAID,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.FUNDED: {
            LoadStatus.PAID,
            LoadStatus.EXCEPTION,
            LoadStatus.ARCHIVED,
        },
        LoadStatus.PAID: {
            LoadStatus.ARCHIVED,
        },
        LoadStatus.EXCEPTION: {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.EXTRACTING,
            LoadStatus.NEEDS_REVIEW,
            LoadStatus.VALIDATED,
            LoadStatus.ARCHIVED,
        },
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