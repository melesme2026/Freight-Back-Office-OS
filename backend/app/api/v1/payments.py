from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.payment_method import PaymentMethod
from app.repositories.payment_method_repo import PaymentMethodRepository
from app.schemas.common import ApiResponse
from app.services.billing.payment_service import PaymentService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _normalize_lower_optional_text(value: str | None) -> str | None:
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


def _to_decimal_string(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _parse_amount(value: str) -> Decimal:
    normalized = _normalize_required_text(value, "amount")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            "Invalid payment amount",
            details={"amount": value},
        ) from exc


def _serialize_payment_method(item: Any) -> dict[str, Any]:
    return {
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
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _serialize_payment(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "billing_invoice_id": str(item.billing_invoice_id)
        if item.billing_invoice_id
        else None,
        "payment_method_id": str(item.payment_method_id)
        if item.payment_method_id
        else None,
        "driver_id": str(item.driver_id) if item.driver_id else None,
        "recorded_by_staff_user_id": str(item.recorded_by_staff_user_id)
        if item.recorded_by_staff_user_id
        else None,
        "provider": str(item.provider),
        "provider_payment_id": item.provider_payment_id,
        "status": str(item.status),
        "amount": _to_decimal_string(item.amount),
        "currency_code": item.currency_code,
        "attempted_at": _to_iso_or_none(item.attempted_at),
        "succeeded_at": _to_iso_or_none(item.succeeded_at),
        "failed_at": _to_iso_or_none(item.failed_at),
        "failure_reason": item.failure_reason,
        "metadata_json": item.metadata_json,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_payment_method_or_404(
    repo: PaymentMethodRepository,
    payment_method_id: uuid.UUID,
) -> PaymentMethod:
    item = repo.get_by_id(payment_method_id)
    if item is None:
        raise NotFoundError(
            "Payment method not found",
            details={"payment_method_id": str(payment_method_id)},
        )
    return item


@router.post("/payment-methods", response_model=ApiResponse)
def create_payment_method(
    *,
    organization_id: uuid.UUID,
    customer_account_id: uuid.UUID,
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
    repo = PaymentMethodRepository(db)

    normalized_provider_payment_method_id = _normalize_required_text(
        provider_payment_method_id,
        "provider_payment_method_id",
    )

    existing = repo.get_by_provider_payment_method_id(
        customer_account_id=customer_account_id,
        provider_payment_method_id=normalized_provider_payment_method_id,
    )
    if existing is not None:
        raise ValidationError(
            "Payment method already exists for customer account",
            details={
                "customer_account_id": str(customer_account_id),
                "provider_payment_method_id": normalized_provider_payment_method_id,
            },
        )

    if is_default:
        repo.clear_default_for_customer_account(customer_account_id)

    item = PaymentMethod(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        provider=_normalize_required_text(provider, "provider"),
        provider_customer_id=_normalize_optional_text(provider_customer_id),
        provider_payment_method_id=normalized_provider_payment_method_id,
        method_type=_normalize_required_text(method_type, "method_type"),
        brand=_normalize_optional_text(brand),
        last4=_normalize_optional_text(last4),
        exp_month=exp_month,
        exp_year=exp_year,
        is_default=is_default,
        is_active=is_active,
    )
    created = repo.create(item)

    return ApiResponse(
        data=_serialize_payment_method(created),
        meta={},
        error=None,
    )


@router.get("/payment-methods", response_model=ApiResponse)
def list_payment_methods(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    provider: str | None = None,
    is_default: bool | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = PaymentMethodRepository(db)
    items, total = repo.list(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        provider=_normalize_optional_text(provider),
        is_default=is_default,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_payment_method(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/payment-methods/{payment_method_id}", response_model=ApiResponse)
def get_payment_method(
    payment_method_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = PaymentMethodRepository(db)
    item = _get_payment_method_or_404(repo, payment_method_id)

    return ApiResponse(
        data=_serialize_payment_method(item),
        meta={},
        error=None,
    )


@router.patch("/payment-methods/{payment_method_id}", response_model=ApiResponse)
def update_payment_method(
    payment_method_id: uuid.UUID,
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
    repo = PaymentMethodRepository(db)
    item = _get_payment_method_or_404(repo, payment_method_id)

    if is_default is True:
        repo.clear_default_for_customer_account(item.customer_account_id)

    if provider_customer_id is not None:
        item.provider_customer_id = _normalize_optional_text(provider_customer_id)
    if brand is not None:
        item.brand = _normalize_optional_text(brand)
    if last4 is not None:
        item.last4 = _normalize_optional_text(last4)
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
        data=_serialize_payment_method(updated),
        meta={},
        error=None,
    )


@router.post("/payments/collect", response_model=ApiResponse)
def collect_payment(
    *,
    organization_id: uuid.UUID,
    customer_account_id: uuid.UUID,
    billing_invoice_id: uuid.UUID,
    amount: str,
    payment_method_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    recorded_by_staff_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = PaymentService(db)
    item = service.collect_payment(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        billing_invoice_id=str(billing_invoice_id),
        amount=_parse_amount(amount),
        payment_method_id=_uuid_to_str(payment_method_id),
        driver_id=_uuid_to_str(driver_id),
        recorded_by_staff_user_id=_uuid_to_str(recorded_by_staff_user_id),
    )

    return ApiResponse(
        data=_serialize_payment(item),
        meta={},
        error=None,
    )


@router.get("/payments", response_model=ApiResponse)
def list_payments(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    billing_invoice_id: uuid.UUID | None = None,
    payment_method_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = PaymentService(db)
    items, total = service.list_payments(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        billing_invoice_id=_uuid_to_str(billing_invoice_id),
        payment_method_id=_uuid_to_str(payment_method_id),
        status=_normalize_lower_optional_text(status),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_payment(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/payments/{payment_id}", response_model=ApiResponse)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = PaymentService(db)
    item = service.get_payment(str(payment_id))

    return ApiResponse(
        data=_serialize_payment(item),
        meta={},
        error=None,
    )


@router.post("/payments/{payment_id}/mark-failed", response_model=ApiResponse)
def mark_payment_failed(
    payment_id: uuid.UUID,
    *,
    failure_reason: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = PaymentService(db)
    item = service.mark_failed(
        payment_id=str(payment_id),
        failure_reason=_normalize_optional_text(failure_reason),
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "status": str(item.status),
            "failed_at": _to_iso_or_none(item.failed_at),
            "failure_reason": item.failure_reason,
            "updated_at": _to_iso_or_none(item.updated_at),
        },
        meta={},
        error=None,
    )