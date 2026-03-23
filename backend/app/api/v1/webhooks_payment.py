from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.ingestion.api_ingestion_service import ApiIngestionService


router = APIRouter()


@router.post("/webhooks/payment", response_model=ApiResponse)
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    payload = await request.json()

    service = ApiIngestionService()
    result = service.ingest(payload)

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )