from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
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
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


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
    )
    created = repo.create(org)

    return ApiResponse(
        data=_serialize_organization(created),
        meta={},
        error=None,
    )


@router.get("/organizations", response_model=ApiResponse)
def list_organizations(
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)
    items = repo.list_all()

    return ApiResponse(
        data=[_serialize_organization(item) for item in items],
        meta={"count": len(items)},
        error=None,
    )


@router.get("/organizations/{organization_id}", response_model=ApiResponse)
def get_organization(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)
    org = _get_organization_or_404(repo, organization_id)

    return ApiResponse(
        data=_serialize_organization(org),
        meta={},
        error=None,
    )