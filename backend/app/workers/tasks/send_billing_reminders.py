from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(
    name="app.workers.tasks.send_billing_reminders",
    queue=WorkerQueues.BILLING,
)
def send_billing_reminders() -> dict:
    return {
        "task": "send_billing_reminders",
        "status": "queued",
    }