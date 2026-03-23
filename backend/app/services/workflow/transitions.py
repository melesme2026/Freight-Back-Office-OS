from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load


class LoadTransitionApplier:
    def apply_status_change(
        self,
        *,
        load: Load,
        new_status: LoadStatus,
    ) -> Load:
        load.status = new_status

        now = datetime.now(timezone.utc)

        if new_status == LoadStatus.SUBMITTED:
            load.submitted_at = now

        if new_status == LoadStatus.FUNDED:
            load.funded_at = now

        if new_status == LoadStatus.PAID:
            load.paid_at = now

        if new_status in {
            LoadStatus.DOCS_RECEIVED,
            LoadStatus.EXTRACTING,
            LoadStatus.NEEDS_REVIEW,
            LoadStatus.VALIDATED,
            LoadStatus.READY_TO_SUBMIT,
        }:
            if new_status == LoadStatus.EXTRACTING:
                load.processing_status = "in_progress"
            elif new_status in {
                LoadStatus.VALIDATED,
                LoadStatus.READY_TO_SUBMIT,
                LoadStatus.SUBMITTED,
                LoadStatus.FUNDED,
                LoadStatus.PAID,
            }:
                load.processing_status = "completed"

        if new_status == LoadStatus.EXCEPTION:
            load.processing_status = "failed"

        return load