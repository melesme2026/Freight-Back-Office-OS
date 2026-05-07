from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.domain.models.demo_request import DemoRequest
from app.schemas.common import ApiResponse
from app.schemas.demo_requests import DemoRequestCreateRequest
from app.services.notifications.operational_notification_service import OperationalNotificationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/demo-requests", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_demo_request(
    payload: DemoRequestCreateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    item = DemoRequest(
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        company=payload.company,
        message=payload.message,
        status="received",
    )
    db.add(item)
    db.flush()
    try:
        OperationalNotificationService(db).demo_request_received(
            demo_request_id=str(item.id),
            full_name=item.full_name,
            email=item.email,
            company=item.company,
            message=item.message,
        )
    except Exception:
        logger.exception("Demo request notification failed", extra={"demo_request_id": str(item.id)})
    db.commit()
    db.refresh(item)
    return ApiResponse(
        data={"id": str(item.id), "status": item.status, "message": "Demo request received."}
    )
