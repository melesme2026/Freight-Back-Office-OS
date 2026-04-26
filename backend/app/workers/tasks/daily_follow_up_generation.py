from __future__ import annotations

import logging

from app.core.database import db_session
from app.domain.models.organization import Organization
from app.services.followups.follow_up_service import FollowUpService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.daily_follow_up_generation")
def daily_follow_up_generation() -> dict[str, int]:
    org_count = 0
    total_tasks = 0
    with db_session() as db:
        orgs = list(db.query(Organization).all())
        service = FollowUpService(db)
        for org in orgs:
            org_count += 1
            try:
                summary = service.generate_followups_for_org(str(org.id))
                total_tasks += int(summary.get("tasks_created_or_updated", 0))
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.exception("daily_follow_up_generation failed for org %s: %s", org.id, exc)
                continue

    logger.info("daily_follow_up_generation completed org_count=%s tasks=%s", org_count, total_tasks)
    return {"organizations_processed": org_count, "tasks_created_or_updated": total_tasks}
