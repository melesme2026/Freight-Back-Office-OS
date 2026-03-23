from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(
    name="app.workers.tasks.mark_overdue_invoices",
    queue=WorkerQueues.BILLING,
)
def mark_overdue_invoices() -> dict:
    return {
        "task": "mark_overdue_invoices",
        "status": "queued",
    }