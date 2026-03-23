from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.common import ApiResponse
from app.services.onboarding.customer_account_service import CustomerAccountService


router = APIRouter()


@router.post("/customer-accounts", response_model=ApiResponse)
def create_customer_account(
    *,
    organization_id: str,
    account_name: str,
    account_code: str | None = None,
    primary_contact_name: str | None = None,
    primary_contact_email: str | None = None,
    primary_contact_phone: str | None = None,
    billing_email: str | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid organization_id",
            details={"organization_id": organization_id},
        ) from exc

    service = CustomerAccountService(db)
    item = service.create_customer_account(
        organization_id=organization_id,
        account_name=account_name,
        account_code=account_code,
        primary_contact_name=primary_contact_name,
        primary_contact_email=primary_contact_email,
        primary_contact_phone=primary_contact_phone,
        billing_email=billing_email,
        notes=notes,
    )

    return ApiResponse(
        data={
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
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/customer-accounts", response_model=ApiResponse)
def list_customer_accounts(
    *,
    organization_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    if organization_id:
        try:
            uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    service = CustomerAccountService(db)
    items, total = service.list_customer_accounts(
        organization_id=organization_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
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


@router.get("/customer-accounts/{customer_account_id}", response_model=ApiResponse)
def get_customer_account(
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

    service = CustomerAccountService(db)
    item = service.get_customer_account(customer_account_id)

    return ApiResponse(
        data={
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
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/customer-accounts/{customer_account_id}", response_model=ApiResponse)
def update_customer_account(
    customer_account_id: str,
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
    try:
        uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid customer_account_id",
            details={"customer_account_id": customer_account_id},
        ) from exc

    service = CustomerAccountService(db)
    item = service.update_customer_account(
        customer_account_id=customer_account_id,
        account_name=account_name,
        account_code=account_code,
        status=status,
        primary_contact_name=primary_contact_name,
        primary_contact_email=primary_contact_email,
        primary_contact_phone=primary_contact_phone,
        billing_email=billing_email,
        notes=notes,
    )

    return ApiResponse(
        data={
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
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )