from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.onboarding.onboarding_service import OnboardingService


router = APIRouter()


@router.post("/onboarding/{customer_account_id}/initialize", response_model=ApiResponse)
def initialize_onboarding(
    customer_account_id: str,
    *,
    organization_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(customer_account_id)
        uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "customer_account_id": customer_account_id,
                "organization_id": organization_id,
            },
        ) from exc

    service = OnboardingService(db)
    item = service.create_or_initialize_checklist(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
    )

    return ApiResponse(
        data={
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
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/onboarding/{customer_account_id}", response_model=ApiResponse)
def get_onboarding(
    customer_account_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid customer_account_id",
            details={"customer_account_id": customer_account_id},
        ) from exc

    service = OnboardingService(db)
    item = service.get_checklist(customer_account_id)

    return ApiResponse(
        data={
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
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.put("/onboarding/{customer_account_id}", response_model=ApiResponse)
def upsert_onboarding(
    customer_account_id: str,
    *,
    organization_id: str,
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
    try:
        uuid.UUID(customer_account_id)
        uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "customer_account_id": customer_account_id,
                "organization_id": organization_id,
            },
        ) from exc

    service = OnboardingService(db)
    item = service.upsert_checklist(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        status=status,
        documents_received=documents_received,
        pricing_confirmed=pricing_confirmed,
        payment_method_added=payment_method_added,
        driver_profiles_created=driver_profiles_created,
        channel_connected=channel_connected,
        go_live_ready=go_live_ready,
        completed_at=completed_at,
    )

    return ApiResponse(
        data={
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
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )