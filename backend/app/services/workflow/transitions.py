from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load import Load


class LoadTransitionApplier:
    def apply_status_change(
        self,
        *,
        load: Load,
        new_status: LoadStatus,
    ) -> Load:
        now = datetime.now(timezone.utc)

        load.status = new_status

        if new_status == LoadStatus.SUBMITTED:
            if load.submitted_at is None:
                load.submitted_at = now

        elif new_status == LoadStatus.FUNDED:
            if load.submitted_at is None:
                load.submitted_at = now
            if load.funded_at is None:
                load.funded_at = now

        elif new_status == LoadStatus.PAID:
            if load.submitted_at is None:
                load.submitted_at = now
            if load.funded_at is None:
                load.funded_at = now
            if load.paid_at is None:
                load.paid_at = now

        if new_status in {LoadStatus.NEW, LoadStatus.DOCS_RECEIVED}:
            load.processing_status = ProcessingStatus.PENDING
        elif new_status == LoadStatus.EXTRACTING:
            load.processing_status = ProcessingStatus.IN_PROGRESS
        elif new_status in {
            LoadStatus.VALIDATED,
            LoadStatus.READY_TO_SUBMIT,
            LoadStatus.SUBMITTED,
            LoadStatus.FUNDED,
            LoadStatus.PAID,
            LoadStatus.ARCHIVED,
        }:
            load.processing_status = ProcessingStatus.COMPLETED
        elif new_status == LoadStatus.EXCEPTION:
            load.processing_status = ProcessingStatus.FAILED

        return load