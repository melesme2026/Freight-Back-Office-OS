from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.send_notification", queue=WorkerQueues.NOTIFICATIONS)
def send_notification(notification_id: str) -> dict:
    return {
        "task": "send_notification",
        "notification_id": notification_id,
        "status": "queued",
    }