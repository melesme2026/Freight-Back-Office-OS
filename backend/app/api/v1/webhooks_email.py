from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.ingestion.email_ingestion_service import EmailIngestionService


router = APIRouter()


def _extract_request_metadata(request: Request) -> dict[str, Any]:
    return {
        "content_type": request.headers.get("content-type"),
        "user_agent": request.headers.get("user-agent"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_request_id": request.headers.get("x-request-id"),
    }


def _ensure_email_webhooks_enabled(settings: Settings) -> None:
    if not settings.email_enabled:
        raise ValidationError(
            "Email integration is not enabled",
            details={"provider": settings.email_provider},
        )

    if settings.email_provider == "none":
        raise ValidationError(
            "Email provider is not configured",
            details={"provider": settings.email_provider},
        )


@router.post("/webhooks/email", response_model=ApiResponse)
async def email_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    _ensure_email_webhooks_enabled(settings)

    try:
        payload = await request.json()
    except Exception as exc:
        raise ValidationError(
            "Invalid JSON payload",
            details={"endpoint": "/webhooks/email"},
        ) from exc

    if not isinstance(payload, dict):
        raise ValidationError(
            "Webhook payload must be a JSON object",
            details={
                "endpoint": "/webhooks/email",
                "payload_type": type(payload).__name__,
            },
        )

    service = EmailIngestionService(db)
    result = service.ingest(
        payload=payload,
        request_metadata=_extract_request_metadata(request),
    )

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )