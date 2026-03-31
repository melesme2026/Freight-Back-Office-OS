from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.onboarding.referral_service import ReferralService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str) -> str:
    return value.strip()


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_referral(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": (
            str(item.customer_account_id) if item.customer_account_id else None
        ),
        "referred_by_name": item.referred_by_name,
        "referred_by_phone": item.referred_by_phone,
        "referred_by_email": item.referred_by_email,
        "notes": item.notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/referrals", response_model=ApiResponse)
def create_referral(
    *,
    organization_id: uuid.UUID,
    referred_by_name: str,
    customer_account_id: uuid.UUID | None = None,
    referred_by_phone: str | None = None,
    referred_by_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ReferralService(db)
    item = service.create_referral(
        organization_id=str(organization_id),
        referred_by_name=_normalize_required_text(referred_by_name),
        customer_account_id=_uuid_to_str(customer_account_id),
        referred_by_phone=_normalize_optional_text(referred_by_phone),
        referred_by_email=_normalize_email(referred_by_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_referral(item),
        meta={},
        error=None,
    )


@router.get("/referrals", response_model=ApiResponse)
def list_referrals(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ReferralService(db)
    items, total = service.list_referrals(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_referral(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/referrals/{referral_id}", response_model=ApiResponse)
def get_referral(
    referral_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ReferralService(db)
    item = service.get_referral(str(referral_id))

    return ApiResponse(
        data=_serialize_referral(item),
        meta={},
        error=None,
    )


@router.patch("/referrals/{referral_id}", response_model=ApiResponse)
def update_referral(
    referral_id: uuid.UUID,
    *,
    customer_account_id: uuid.UUID | None = None,
    referred_by_name: str | None = None,
    referred_by_phone: str | None = None,
    referred_by_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ReferralService(db)
    item = service.update_referral(
        referral_id=str(referral_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        referred_by_name=(
            _normalize_required_text(referred_by_name)
            if referred_by_name is not None
            else None
        ),
        referred_by_phone=_normalize_optional_text(referred_by_phone),
        referred_by_email=_normalize_email(referred_by_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_referral(item),
        meta={},
        error=None,
    )