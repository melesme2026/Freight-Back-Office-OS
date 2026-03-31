from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.organization import Organization
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.common import ApiResponse


router = APIRouter()


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"{field_name} is required",
            details={field_name: value},
        )
    return normalized


def _normalize_slug(value: str) -> str:
    normalized = _normalize_required_text(value, "slug").lower()
    return normalized


def _serialize_organization(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "slug": item.slug,
        "is_active": item.is_active,
    }


def _get_organization_or_404(
    repo: OrganizationRepository, organization_id: uuid.UUID
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
    *,
    name: str,
    slug: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)

    normalized_name = _normalize_required_text(name, "name")
    normalized_slug = _normalize_slug(slug)

    existing = repo.get_by_slug(normalized_slug)
    if existing is not None:
        raise ValidationError(
            "Organization slug already exists",
            details={"slug": normalized_slug},
        )

    org = Organization(
        name=normalized_name,
        slug=normalized_slug,
        is_active=True,
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