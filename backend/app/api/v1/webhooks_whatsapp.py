from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.ingestion.whatsapp_ingestion_service import WhatsAppIngestionService


router = APIRouter()


@router.post("/webhooks/whatsapp", response_model=ApiResponse)
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    payload = await request.json()

    service = WhatsAppIngestionService()
    result = service.ingest(payload)

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )