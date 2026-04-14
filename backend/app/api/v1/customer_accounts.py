from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.onboarding.customer_account_service import CustomerAccountService


router = APIRouter()


class CustomerAccountCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    account_name: str
    account_code: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    billing_email: str | None = None
    notes: str | None = None


class CustomerAccountUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_name: str | None = None
    account_code: str | None = None
    status: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    billing_email: str | None = None
    notes: str | None = None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name.replace('_', ' ').capitalize()} is required.",
            details={field_name: "This field cannot be blank."},
        )
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _serialize_customer_account(item: Any) -> dict[str, Any]:
    drivers = getattr(item, "drivers", None)
    loads = getattr(item, "loads", None)

    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "account_name": item.account_name,
        "account_code": item.account_code,
        "status": _enum_to_string(item.status),
        "primary_contact_name": item.primary_contact_name,
        "primary_contact_email": item.primary_contact_email,
        "primary_contact_phone": item.primary_contact_phone,
        "billing_email": item.billing_email,
        "notes": item.notes,
        "driver_count": len(drivers) if isinstance(drivers, list) else None,
        "load_count": len(loads) if isinstance(loads, list) else None,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/customer-accounts", response_model=ApiResponse)
def create_customer_account(
    payload: CustomerAccountCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    service = CustomerAccountService(db)
    item = service.create_customer_account(
        organization_id=str(payload.organization_id),
        account_name=_normalize_required_text(payload.account_name, field_name="account_name"),
        account_code=_normalize_optional_text(payload.account_code),
        primary_contact_name=_normalize_optional_text(payload.primary_contact_name),
        primary_contact_email=_normalize_email(payload.primary_contact_email),
        primary_contact_phone=_normalize_optional_text(payload.primary_contact_phone),
        billing_email=_normalize_email(payload.billing_email),
        notes=_normalize_optional_text(payload.notes),
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    service = CustomerAccountService(db)
    items, total = service.list_customer_accounts(
        organization_id=str(effective_org_id),
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
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    item = service.get_customer_account(str(customer_account_id))
    token_org_id = token_payload.get("organization_id")
    if str(item.organization_id) != str(token_org_id):
        raise UnauthorizedError("Customer account is not in authenticated organization")

    return ApiResponse(
        data=_serialize_customer_account(item),
        meta={},
        error=None,
    )


@router.patch("/customer-accounts/{customer_account_id}", response_model=ApiResponse)
def update_customer_account(
    customer_account_id: uuid.UUID,
    payload: CustomerAccountUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = CustomerAccountService(db)
    existing = service.get_customer_account(str(customer_account_id))
    token_org_id = token_payload.get("organization_id")
    if str(existing.organization_id) != str(token_org_id):
        raise UnauthorizedError("Customer account is not in authenticated organization")

    item = service.update_customer_account(
        customer_account_id=str(customer_account_id),
        account_name=(
            _normalize_required_text(payload.account_name, field_name="account_name")
            if payload.account_name is not None
            else None
        ),
        account_code=_normalize_optional_text(payload.account_code),
        status=_normalize_optional_text(payload.status),
        primary_contact_name=_normalize_optional_text(payload.primary_contact_name),
        primary_contact_email=_normalize_email(payload.primary_contact_email),
        primary_contact_phone=_normalize_optional_text(payload.primary_contact_phone),
        billing_email=_normalize_email(payload.billing_email),
        notes=_normalize_optional_text(payload.notes),
    )

    return ApiResponse(
        data=_serialize_customer_account(item),
        meta={},
        error=None,
    )
