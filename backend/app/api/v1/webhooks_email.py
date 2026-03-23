from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.ingestion.email_ingestion_service import EmailIngestionService


router = APIRouter()


@router.post("/webhooks/email", response_model=ApiResponse)
async def email_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    payload = await request.json()

    service = EmailIngestionService()
    result = service.ingest(payload)

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )