from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.onboarding.customer_account_service import CustomerAccountService


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


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _serialize_customer_account(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "account_name": item.account_name,
        "account_code": item.account_code,
        "status": str(item.status),
        "primary_contact_name": item.primary_contact_name,
        "primary_contact_email": item.primary_contact_email,
        "primary_contact_phone": item.primary_contact_phone,
        "billing_email": item.billing_email,
        "notes": item.notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/customer-accounts", response_model=ApiResponse)
def create_customer_account(
    *,
    organization_id: uuid.UUID,
    account_name: str,
    account_code: str | None = None,
    primary_contact_name: str | None = None,
    primary_contact_email: str | None = None,
    primary_contact_phone: str | None = None,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    item = service.create_customer_account(
        organization_id=str(organization_id),
        account_name=account_name.strip(),
        account_code=_normalize_optional_text(account_code),
        primary_contact_name=_normalize_optional_text(primary_contact_name),
        primary_contact_email=_normalize_email(primary_contact_email),
        primary_contact_phone=_normalize_optional_text(primary_contact_phone),
        billing_email=_normalize_email(billing_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_customer_account(item),
        meta={},
        error=None,
    )


@router.get("/customer-accounts", response_model=ApiResponse)
def list_customer_accounts(
    *,
    organization_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    items, total = service.list_customer_accounts(
        organization_id=str(organization_id) if organization_id else None,
        status=_normalize_optional_text(status),
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_customer_account(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/customer-accounts/{customer_account_id}", response_model=ApiResponse)
def get_customer_account(
    customer_account_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    item = service.get_customer_account(str(customer_account_id))

    return ApiResponse(
        data=_serialize_customer_account(item),
        meta={},
        error=None,
    )


@router.patch("/customer-accounts/{customer_account_id}", response_model=ApiResponse)
def update_customer_account(
    customer_account_id: uuid.UUID,
    *,
    account_name: str | None = None,
    account_code: str | None = None,
    status: str | None = None,
    primary_contact_name: str | None = None,
    primary_contact_email: str | None = None,
    primary_contact_phone: str | None = None,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    item = service.update_customer_account(
        customer_account_id=str(customer_account_id),
        account_name=account_name.strip() if account_name is not None else None,
        account_code=_normalize_optional_text(account_code),
        status=_normalize_optional_text(status),
        primary_contact_name=_normalize_optional_text(primary_contact_name),
        primary_contact_email=_normalize_email(primary_contact_email),
        primary_contact_phone=_normalize_optional_text(primary_contact_phone),
        billing_email=_normalize_email(billing_email),
        notes=notes,
    )

    return ApiResponse(
        data=_serialize_customer_account(item),
        meta={},
        error=None,
    )