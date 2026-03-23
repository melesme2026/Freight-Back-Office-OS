from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.onboarding.referral_service import ReferralService


router = APIRouter()


@router.post("/referrals", response_model=ApiResponse)
def create_referral(
    *,
    organization_id: str,
    referred_by_name: str,
    customer_account_id: str | None = None,
    referred_by_phone: str | None = None,
    referred_by_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    service = ReferralService(db)
    item = service.create_referral(
        organization_id=organization_id,
        referred_by_name=referred_by_name,
        customer_account_id=customer_account_id,
        referred_by_phone=referred_by_phone,
        referred_by_email=referred_by_email,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "referred_by_name": item.referred_by_name,
            "referred_by_phone": item.referred_by_phone,
            "referred_by_email": item.referred_by_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/referrals", response_model=ApiResponse)
def list_referrals(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    service = ReferralService(db)
    items, total = service.list_referrals(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
                "referred_by_name": item.referred_by_name,
                "referred_by_phone": item.referred_by_phone,
                "referred_by_email": item.referred_by_email,
                "notes": item.notes,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/referrals/{referral_id}", response_model=ApiResponse)
def get_referral(
    referral_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(referral_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid referral_id",
            details={"referral_id": referral_id},
        ) from exc

    service = ReferralService(db)
    item = service.get_referral(referral_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "referred_by_name": item.referred_by_name,
            "referred_by_phone": item.referred_by_phone,
            "referred_by_email": item.referred_by_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/referrals/{referral_id}", response_model=ApiResponse)
def update_referral(
    referral_id: str,
    *,
    customer_account_id: str | None = None,
    referred_by_name: str | None = None,
    referred_by_phone: str | None = None,
    referred_by_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(referral_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "referral_id": referral_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    service = ReferralService(db)
    item = service.update_referral(
        referral_id=referral_id,
        customer_account_id=customer_account_id,
        referred_by_name=referred_by_name,
        referred_by_phone=referred_by_phone,
        referred_by_email=referred_by_email,
        notes=notes,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id) if item.customer_account_id else None,
            "referred_by_name": item.referred_by_name,
            "referred_by_phone": item.referred_by_phone,
            "referred_by_email": item.referred_by_email,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )