from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(
    name="app.workers.tasks.generate_recurring_invoices",
    queue=WorkerQueues.BILLING,
)
def generate_recurring_invoices() -> dict:
    return {
        "task": "generate_recurring_invoices",
        "status": "queued",
    }