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

        if new_status in {
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
        } and load.submitted_at is None:
            load.submitted_at = now

        if new_status == LoadStatus.ADVANCE_PAID and load.funded_at is None:
            if load.submitted_at is None:
                load.submitted_at = now
            load.funded_at = now

        if new_status in {LoadStatus.FULLY_PAID, LoadStatus.SHORT_PAID} and load.paid_at is None:
            if load.submitted_at is None:
                load.submitted_at = now
            load.paid_at = now

        if new_status in {
            LoadStatus.BOOKED,
            LoadStatus.IN_TRANSIT,
            LoadStatus.DELIVERED,
            LoadStatus.DOCS_RECEIVED,
        }:
            load.processing_status = ProcessingStatus.PENDING
        elif new_status == LoadStatus.DOCS_NEEDS_ATTENTION:
            load.processing_status = ProcessingStatus.FAILED
        else:
            load.processing_status = ProcessingStatus.COMPLETED

        return load
