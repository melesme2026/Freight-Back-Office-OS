from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.ingestion.api_ingestion_service import ApiIngestionService


router = APIRouter()


def _extract_request_metadata(request: Request) -> dict[str, Any]:
    return {
        "content_type": request.headers.get("content-type"),
        "user_agent": request.headers.get("user-agent"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_request_id": request.headers.get("x-request-id"),
    }


def _ensure_payment_webhooks_enabled(settings: Settings) -> None:
    if not settings.billing_enabled:
        raise ValidationError(
            "Billing integration is not enabled",
            details={"payment_provider": settings.payment_provider},
        )

    if settings.payment_provider == "none":
        raise ValidationError(
            "Payment provider is not configured",
            details={"payment_provider": settings.payment_provider},
        )


@router.post("/webhooks/payment", response_model=ApiResponse)
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    _ensure_payment_webhooks_enabled(settings)

    try:
        payload = await request.json()
    except Exception as exc:
        raise ValidationError(
            "Invalid JSON payload",
            details={"endpoint": "/webhooks/payment"},
        ) from exc

    if not isinstance(payload, dict):
        raise ValidationError(
            "Webhook payload must be a JSON object",
            details={
                "endpoint": "/webhooks/payment",
                "payload_type": type(payload).__name__,
            },
        )

    service = ApiIngestionService(db)
    result = service.ingest(
        payload=payload,
        request_metadata=_extract_request_metadata(request),
    )

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )