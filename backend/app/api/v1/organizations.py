from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.core.security import get_current_token_payload
from app.domain.models.organization import Organization
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.common import ApiResponse


router = APIRouter()


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str
    legal_name: str | None = None
    email: str | None = None
    phone: str | None = None
    timezone: str | None = None
    currency_code: str | None = None
    is_active: bool = True
    billing_provider: str | None = None
    billing_status: str | None = None
    plan_code: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_notes: str | None = None


class OrganizationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    slug: str | None = None
    legal_name: str | None = None
    email: str | None = None
    phone: str | None = None
    timezone: str | None = None
    currency_code: str | None = None
    is_active: bool | None = None
    billing_provider: str | None = None
    billing_status: str | None = None
    plan_code: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_notes: str | None = None


ALLOWED_BILLING_PROVIDERS = {"stripe", "manual", "none"}
ALLOWED_BILLING_STATUSES = {"trial", "active", "manual_active", "inactive", "past_due", "canceled"}
ALLOWED_PLAN_CODES = {"starter", "growth", "enterprise", "none"}


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_slug(value: str) -> str:
    return _normalize_required_text(value, "slug").lower()


def _normalize_email(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _normalize_currency_code(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.upper() if normalized else None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_organization(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "slug": item.slug,
        "legal_name": item.legal_name,
        "email": item.email,
        "phone": item.phone,
        "timezone": item.timezone,
        "currency_code": item.currency_code,
        "is_active": item.is_active,
        "billing_provider": item.billing_provider,
        "billing_status": item.billing_status,
        "plan_code": item.plan_code,
        "stripe_customer_id": item.stripe_customer_id,
        "stripe_subscription_id": item.stripe_subscription_id,
        "billing_notes": item.billing_notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _normalize_billing_provider(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered not in ALLOWED_BILLING_PROVIDERS:
        raise ValidationError("Invalid billing_provider", details={"billing_provider": value})
    return lowered


def _normalize_billing_status(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered not in ALLOWED_BILLING_STATUSES:
        raise ValidationError("Invalid billing_status", details={"billing_status": value})
    return lowered


def _normalize_plan_code(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered not in ALLOWED_PLAN_CODES:
        raise ValidationError("Invalid plan_code", details={"plan_code": value})
    return lowered


def _assert_billing_admin_role(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in {"owner", "admin", "ops_manager", "billing_admin"}:
        raise UnauthorizedError("Insufficient privileges to modify organization billing settings")


def _get_organization_or_404(
    repo: OrganizationRepository,
    organization_id: uuid.UUID,
) -> Organization:
    item = repo.get_by_id(organization_id)
    if item is None:
        raise NotFoundError(
            "Organization not found",
            details={"organization_id": str(organization_id)},
        )
    return item


def _assert_token_org_access(
    *,
    token_payload: dict[str, Any],
    organization_id: uuid.UUID,
) -> None:
    token_org_id = str(token_payload.get("organization_id") or "").strip()
    if not token_org_id:
        raise UnauthorizedError("Token organization_id is missing")
    if token_org_id != str(organization_id):
        raise UnauthorizedError("Cannot access another organization")


@router.post("/organizations", response_model=ApiResponse)
def create_organization(
    payload: OrganizationCreateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)

    normalized_name = _normalize_required_text(payload.name, "name")
    normalized_slug = _normalize_slug(payload.slug)

    existing = repo.get_by_slug(normalized_slug)
    if existing is not None:
        raise ValidationError(
            "Organization slug already exists",
            details={"slug": normalized_slug},
        )

    org = Organization(
        name=normalized_name,
        slug=normalized_slug,
        legal_name=_normalize_optional_text(payload.legal_name),
        email=_normalize_email(payload.email),
        phone=_normalize_optional_text(payload.phone),
        timezone=_normalize_optional_text(payload.timezone) or "America/Toronto",
        currency_code=_normalize_currency_code(payload.currency_code) or "USD",
        is_active=payload.is_active,
        billing_provider=_normalize_billing_provider(payload.billing_provider) or "none",
        billing_status=_normalize_billing_status(payload.billing_status) or "trial",
        plan_code=_normalize_plan_code(payload.plan_code) or "none",
        stripe_customer_id=_normalize_optional_text(payload.stripe_customer_id),
        stripe_subscription_id=_normalize_optional_text(payload.stripe_subscription_id),
        billing_notes=_normalize_optional_text(payload.billing_notes),
    )
    created = repo.create(org)

    return ApiResponse(
        data=_serialize_organization(created),
        meta={},
        error=None,
    )


@router.get("/organizations", response_model=ApiResponse)
def list_organizations(
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)
    token_org_id = str(token_payload.get("organization_id") or "").strip()
    if not token_org_id:
        raise UnauthorizedError("Token organization_id is missing")
    item = repo.get_by_id(token_org_id)
    items = [item] if item is not None else []

    return ApiResponse(
        data=[_serialize_organization(item) for item in items],
        meta={"count": len(items)},
        error=None,
    )


@router.get("/organizations/{organization_id}", response_model=ApiResponse)
def get_organization(
    organization_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_token_org_access(token_payload=token_payload, organization_id=organization_id)
    repo = OrganizationRepository(db)
    org = _get_organization_or_404(repo, organization_id)

    return ApiResponse(
        data=_serialize_organization(org),
        meta={},
        error=None,
    )


@router.patch("/organizations/{organization_id}", response_model=ApiResponse)
def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_token_org_access(token_payload=token_payload, organization_id=organization_id)
    repo = OrganizationRepository(db)
    org = _get_organization_or_404(repo, organization_id)

    if payload.name is not None:
        org.name = _normalize_required_text(payload.name, "name")

    if payload.slug is not None:
        normalized_slug = _normalize_slug(payload.slug)
        existing = repo.get_by_slug(normalized_slug)
        if existing is not None and existing.id != org.id:
            raise ValidationError(
                "Organization slug already exists",
                details={"slug": normalized_slug},
            )
        org.slug = normalized_slug

    if payload.legal_name is not None:
        org.legal_name = _normalize_optional_text(payload.legal_name)

    if payload.email is not None:
        org.email = _normalize_email(payload.email)

    if payload.phone is not None:
        org.phone = _normalize_optional_text(payload.phone)

    if payload.timezone is not None:
        org.timezone = _normalize_required_text(payload.timezone, "timezone")

    if payload.currency_code is not None:
        org.currency_code = _normalize_currency_code(payload.currency_code) or org.currency_code

    if payload.is_active is not None:
        org.is_active = payload.is_active

    if (
        payload.billing_provider is not None
        or payload.billing_status is not None
        or payload.plan_code is not None
        or payload.stripe_customer_id is not None
        or payload.stripe_subscription_id is not None
        or payload.billing_notes is not None
    ):
        _assert_billing_admin_role(token_payload)

        if payload.billing_provider is not None:
            org.billing_provider = _normalize_billing_provider(payload.billing_provider) or org.billing_provider

        if payload.billing_status is not None:
            org.billing_status = _normalize_billing_status(payload.billing_status) or org.billing_status

        if payload.plan_code is not None:
            org.plan_code = _normalize_plan_code(payload.plan_code) or org.plan_code

        if payload.stripe_customer_id is not None:
            org.stripe_customer_id = _normalize_optional_text(payload.stripe_customer_id)

        if payload.stripe_subscription_id is not None:
            org.stripe_subscription_id = _normalize_optional_text(payload.stripe_subscription_id)

        if payload.billing_notes is not None:
            org.billing_notes = _normalize_optional_text(payload.billing_notes)

    updated = repo.update(org)

    return ApiResponse(
        data=_serialize_organization(updated),
        meta={},
        error=None,
    )
