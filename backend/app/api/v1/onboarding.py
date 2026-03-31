from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.onboarding.onboarding_service import OnboardingService


router = APIRouter()


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _normalize_required_text(value: str) -> str:
    return value.strip()


def _serialize_onboarding_checklist(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "status": str(item.status),
        "documents_received": item.documents_received,
        "pricing_confirmed": item.pricing_confirmed,
        "payment_method_added": item.payment_method_added,
        "driver_profiles_created": item.driver_profiles_created,
        "channel_connected": item.channel_connected,
        "go_live_ready": item.go_live_ready,
        "completed_at": _to_iso_or_none(item.completed_at),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/onboarding/{customer_account_id}/initialize", response_model=ApiResponse)
def initialize_onboarding(
    customer_account_id: uuid.UUID,
    *,
    organization_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = OnboardingService(db)
    item = service.create_or_initialize_checklist(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
    )

    return ApiResponse(
        data=_serialize_onboarding_checklist(item),
        meta={},
        error=None,
    )


@router.get("/onboarding/{customer_account_id}", response_model=ApiResponse)
def get_onboarding(
    customer_account_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = OnboardingService(db)
    item = service.get_checklist(str(customer_account_id))

    return ApiResponse(
        data=_serialize_onboarding_checklist(item),
        meta={},
        error=None,
    )


@router.put("/onboarding/{customer_account_id}", response_model=ApiResponse)
def upsert_onboarding(
    customer_account_id: uuid.UUID,
    *,
    organization_id: uuid.UUID,
    status: str,
    documents_received: bool,
    pricing_confirmed: bool,
    payment_method_added: bool,
    driver_profiles_created: bool,
    channel_connected: bool,
    go_live_ready: bool,
    completed_at: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = OnboardingService(db)
    item = service.upsert_checklist(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        status=_normalize_required_text(status),
        documents_received=documents_received,
        pricing_confirmed=pricing_confirmed,
        payment_method_added=payment_method_added,
        driver_profiles_created=driver_profiles_created,
        channel_connected=channel_connected,
        go_live_ready=go_live_ready,
        completed_at=completed_at,
    )

    return ApiResponse(
        data=_serialize_onboarding_checklist(item),
        meta={},
        error=None,
    )