from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.payment_method import PaymentMethod
from app.repositories.payment_method_repo import PaymentMethodRepository
from app.schemas.common import ApiResponse
from app.services.billing.payment_service import PaymentService


router = APIRouter()


@router.post("/payment-methods", response_model=ApiResponse)
def create_payment_method(
    *,
    organization_id: str,
    customer_account_id: str,
    provider: str,
    provider_payment_method_id: str,
    method_type: str,
    provider_customer_id: str | None = None,
    brand: str | None = None,
    last4: str | None = None,
    exp_month: int | None = None,
    exp_year: int | None = None,
    is_default: bool = False,
    is_active: bool = True,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id)
        parsed_customer_account_id = uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    repo = PaymentMethodRepository(db)

    existing = repo.get_by_provider_payment_method_id(
        customer_account_id=parsed_customer_account_id,
        provider_payment_method_id=provider_payment_method_id,
    )
    if existing is not None:
        raise ValidationError(
            "Payment method already exists for customer account",
            details={
                "customer_account_id": customer_account_id,
                "provider_payment_method_id": provider_payment_method_id,
            },
        )

    if is_default:
        repo.clear_default_for_customer_account(parsed_customer_account_id)

    item = PaymentMethod(
        organization_id=parsed_organization_id,
        customer_account_id=parsed_customer_account_id,
        provider=provider,
        provider_customer_id=provider_customer_id,
        provider_payment_method_id=provider_payment_method_id,
        method_type=method_type,
        brand=brand,
        last4=last4,
        exp_month=exp_month,
        exp_year=exp_year,
        is_default=is_default,
        is_active=is_active,
    )
    created = repo.create(item)

    return ApiResponse(
        data={
            "id": str(created.id),
            "organization_id": str(created.organization_id),
            "customer_account_id": str(created.customer_account_id),
            "provider": str(created.provider),
            "provider_customer_id": created.provider_customer_id,
            "provider_payment_method_id": created.provider_payment_method_id,
            "method_type": str(created.method_type),
            "brand": created.brand,
            "last4": created.last4,
            "exp_month": created.exp_month,
            "exp_year": created.exp_year,
            "is_default": created.is_default,
            "is_active": created.is_active,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/payment-methods", response_model=ApiResponse)
def list_payment_methods(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    provider: str | None = None,
    is_default: bool | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    parsed_organization_id = None
    parsed_customer_account_id = None

    try:
        if organization_id:
            parsed_organization_id = uuid.UUID(organization_id)
        if customer_account_id:
            parsed_customer_account_id = uuid.UUID(customer_account_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
            },
        ) from exc

    repo = PaymentMethodRepository(db)
    items, total = repo.list(
        organization_id=parsed_organization_id,
        customer_account_id=parsed_customer_account_id,
        provider=provider,
        is_default=is_default,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "provider": str(item.provider),
                "provider_customer_id": item.provider_customer_id,
                "provider_payment_method_id": item.provider_payment_method_id,
                "method_type": str(item.method_type),
                "brand": item.brand,
                "last4": item.last4,
                "exp_month": item.exp_month,
                "exp_year": item.exp_year,
                "is_default": item.is_default,
                "is_active": item.is_active,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/payment-methods/{payment_method_id}", response_model=ApiResponse)
def get_payment_method(
    payment_method_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_payment_method_id = uuid.UUID(payment_method_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid payment_method_id",
            details={"payment_method_id": payment_method_id},
        ) from exc

    repo = PaymentMethodRepository(db)
    item = repo.get_by_id(parsed_payment_method_id)
    if item is None:
        raise NotFoundError(
            "Payment method not found",
            details={"payment_method_id": payment_method_id},
        )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "provider": str(item.provider),
            "provider_customer_id": item.provider_customer_id,
            "provider_payment_method_id": item.provider_payment_method_id,
            "method_type": str(item.method_type),
            "brand": item.brand,
            "last4": item.last4,
            "exp_month": item.exp_month,
            "exp_year": item.exp_year,
            "is_default": item.is_default,
            "is_active": item.is_active,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/payment-methods/{payment_method_id}", response_model=ApiResponse)
def update_payment_method(
    payment_method_id: str,
    *,
    provider_customer_id: str | None = None,
    brand: str | None = None,
    last4: str | None = None,
    exp_month: int | None = None,
    exp_year: int | None = None,
    is_default: bool | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_payment_method_id = uuid.UUID(payment_method_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid payment_method_id",
            details={"payment_method_id": payment_method_id},
        ) from exc

    repo = PaymentMethodRepository(db)
    item = repo.get_by_id(parsed_payment_method_id)
    if item is None:
        raise NotFoundError(
            "Payment method not found",
            details={"payment_method_id": payment_method_id},
        )

    if is_default is True:
        repo.clear_default_for_customer_account(item.customer_account_id)

    if provider_customer_id is not None:
        item.provider_customer_id = provider_customer_id
    if brand is not None:
        item.brand = brand
    if last4 is not None:
        item.last4 = last4
    if exp_month is not None:
        item.exp_month = exp_month
    if exp_year is not None:
        item.exp_year = exp_year
    if is_default is not None:
        item.is_default = is_default
    if is_active is not None:
        item.is_active = is_active

    updated = repo.update(item)

    return ApiResponse(
        data={
            "id": str(updated.id),
            "organization_id": str(updated.organization_id),
            "customer_account_id": str(updated.customer_account_id),
            "provider": str(updated.provider),
            "provider_customer_id": updated.provider_customer_id,
            "provider_payment_method_id": updated.provider_payment_method_id,
            "method_type": str(updated.method_type),
            "brand": updated.brand,
            "last4": updated.last4,
            "exp_month": updated.exp_month,
            "exp_year": updated.exp_year,
            "is_default": updated.is_default,
            "is_active": updated.is_active,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/payments/collect", response_model=ApiResponse)
def collect_payment(
    *,
    organization_id: str,
    customer_account_id: str,
    billing_invoice_id: str,
    amount: str,
    payment_method_id: str | None = None,
    driver_id: str | None = None,
    recorded_by_staff_user_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        uuid.UUID(customer_account_id)
        uuid.UUID(billing_invoice_id)
        if payment_method_id:
            uuid.UUID(payment_method_id)
        if driver_id:
            uuid.UUID(driver_id)
        if recorded_by_staff_user_id:
            uuid.UUID(recorded_by_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "billing_invoice_id": billing_invoice_id,
                "payment_method_id": payment_method_id,
                "driver_id": driver_id,
                "recorded_by_staff_user_id": recorded_by_staff_user_id,
            },
        ) from exc

    try:
        parsed_amount = Decimal(amount)
    except Exception as exc:
        raise ValidationError(
            "Invalid payment amount",
            details={"amount": amount},
        ) from exc

    service = PaymentService(db)
    item = service.collect_payment(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        billing_invoice_id=billing_invoice_id,
        amount=parsed_amount,
        payment_method_id=payment_method_id,
        driver_id=driver_id,
        recorded_by_staff_user_id=recorded_by_staff_user_id,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "billing_invoice_id": str(item.billing_invoice_id) if item.billing_invoice_id else None,
            "payment_method_id": str(item.payment_method_id) if item.payment_method_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "recorded_by_staff_user_id": str(item.recorded_by_staff_user_id) if item.recorded_by_staff_user_id else None,
            "provider": str(item.provider),
            "provider_payment_id": item.provider_payment_id,
            "status": str(item.status),
            "amount": format(item.amount, "f"),
            "currency_code": item.currency_code,
            "attempted_at": item.attempted_at.isoformat() if item.attempted_at else None,
            "succeeded_at": item.succeeded_at.isoformat() if item.succeeded_at else None,
            "failed_at": item.failed_at.isoformat() if item.failed_at else None,
            "failure_reason": item.failure_reason,
            "metadata_json": item.metadata_json,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/payments", response_model=ApiResponse)
def list_payments(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    billing_invoice_id: str | None = None,
    payment_method_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if billing_invoice_id:
            uuid.UUID(billing_invoice_id)
        if payment_method_id:
            uuid.UUID(payment_method_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "billing_invoice_id": billing_invoice_id,
                "payment_method_id": payment_method_id,
            },
        ) from exc

    service = PaymentService(db)
    items, total = service.list_payments(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        billing_invoice_id=billing_invoice_id,
        payment_method_id=payment_method_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "billing_invoice_id": str(item.billing_invoice_id) if item.billing_invoice_id else None,
                "payment_method_id": str(item.payment_method_id) if item.payment_method_id else None,
                "driver_id": str(item.driver_id) if item.driver_id else None,
                "recorded_by_staff_user_id": str(item.recorded_by_staff_user_id) if item.recorded_by_staff_user_id else None,
                "provider": str(item.provider),
                "provider_payment_id": item.provider_payment_id,
                "status": str(item.status),
                "amount": format(item.amount, "f"),
                "currency_code": item.currency_code,
                "attempted_at": item.attempted_at.isoformat() if item.attempted_at else None,
                "succeeded_at": item.succeeded_at.isoformat() if item.succeeded_at else None,
                "failed_at": item.failed_at.isoformat() if item.failed_at else None,
                "failure_reason": item.failure_reason,
                "metadata_json": item.metadata_json,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/payments/{payment_id}", response_model=ApiResponse)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(payment_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid payment_id",
            details={"payment_id": payment_id},
        ) from exc

    service = PaymentService(db)
    item = service.get_payment(payment_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "billing_invoice_id": str(item.billing_invoice_id) if item.billing_invoice_id else None,
            "payment_method_id": str(item.payment_method_id) if item.payment_method_id else None,
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "recorded_by_staff_user_id": str(item.recorded_by_staff_user_id) if item.recorded_by_staff_user_id else None,
            "provider": str(item.provider),
            "provider_payment_id": item.provider_payment_id,
            "status": str(item.status),
            "amount": format(item.amount, "f"),
            "currency_code": item.currency_code,
            "attempted_at": item.attempted_at.isoformat() if item.attempted_at else None,
            "succeeded_at": item.succeeded_at.isoformat() if item.succeeded_at else None,
            "failed_at": item.failed_at.isoformat() if item.failed_at else None,
            "failure_reason": item.failure_reason,
            "metadata_json": item.metadata_json,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/payments/{payment_id}/mark-failed", response_model=ApiResponse)
def mark_payment_failed(
    payment_id: str,
    *,
    failure_reason: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(payment_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid payment_id",
            details={"payment_id": payment_id},
        ) from exc

    service = PaymentService(db)
    item = service.mark_failed(
        payment_id=payment_id,
        failure_reason=failure_reason,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "failed_at": item.failed_at.isoformat() if item.failed_at else None,
            "failure_reason": item.failure_reason,
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )