from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.ingestion.whatsapp_ingestion_service import (
    WhatsAppIngestionService,
)


router = APIRouter()


def _extract_request_metadata(request: Request) -> dict[str, Any]:
    return {
        "content_type": request.headers.get("content-type"),
        "user_agent": request.headers.get("user-agent"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_request_id": request.headers.get("x-request-id"),
    }


def _ensure_whatsapp_webhooks_enabled(settings: Settings) -> None:
    if not settings.whatsapp_enabled:
        raise ValidationError(
            "WhatsApp integration is not enabled",
            details={"provider": settings.whatsapp_provider},
        )

    if settings.whatsapp_provider == "none":
        raise ValidationError(
            "WhatsApp provider is not configured",
            details={"provider": settings.whatsapp_provider},
        )


@router.get("/webhooks/whatsapp", response_model=ApiResponse)
async def verify_whatsapp_webhook(
    *,
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    _ensure_whatsapp_webhooks_enabled(settings)

    if settings.whatsapp_provider != "meta":
        return ApiResponse(
            data={
                "verified": False,
                "provider": settings.whatsapp_provider,
                "reason": "verification_not_required_for_provider",
            },
            meta={},
            error=None,
        )

    expected_token = (settings.whatsapp_verify_token or "").strip()

    if hub_mode != "subscribe":
        raise ValidationError(
            "Invalid webhook verification mode",
            details={"hub.mode": hub_mode},
        )

    if not expected_token:
        raise ValidationError(
            "WhatsApp verify token is not configured",
            details={"provider": settings.whatsapp_provider},
        )

    if hub_verify_token != expected_token:
        raise ValidationError(
            "Invalid webhook verify token",
            details={"provider": settings.whatsapp_provider},
        )

    if not hub_challenge:
        raise ValidationError(
            "Missing webhook challenge",
            details={"provider": settings.whatsapp_provider},
        )

    return ApiResponse(
        data={
            "verified": True,
            "challenge": hub_challenge,
            "provider": settings.whatsapp_provider,
        },
        meta={},
        error=None,
    )


@router.post("/webhooks/whatsapp", response_model=ApiResponse)
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    _ensure_whatsapp_webhooks_enabled(settings)

    try:
        payload = await request.json()
    except Exception as exc:
        raise ValidationError(
            "Invalid JSON payload",
            details={"endpoint": "/webhooks/whatsapp"},
        ) from exc

    if not isinstance(payload, dict):
        raise ValidationError(
            "Webhook payload must be a JSON object",
            details={
                "endpoint": "/webhooks/whatsapp",
                "payload_type": type(payload).__name__,
            },
        )

    service = WhatsAppIngestionService(db)
    result = service.ingest(
        payload=payload,
        request_metadata=_extract_request_metadata(request),
    )

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )