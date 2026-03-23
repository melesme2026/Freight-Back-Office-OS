from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.organization import Organization
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.post("/organizations", response_model=ApiResponse)
def create_organization(
    *,
    name: str,
    slug: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)

    existing = repo.get_by_slug(slug)
    if existing:
        raise ValidationError(
            "Organization slug already exists",
            details={"slug": slug},
        )

    org = Organization(
        name=name,
        slug=slug,
        is_active=True,
    )

    created = repo.create(org)

    return ApiResponse(
        data={
            "id": str(created.id),
            "name": created.name,
            "slug": created.slug,
            "is_active": created.is_active,
        },
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
        data=[
            {
                "id": str(item.id),
                "name": item.name,
                "slug": item.slug,
                "is_active": item.is_active,
            }
            for item in items
        ],
        meta={"count": len(items)},
        error=None,
    )


@router.get("/organizations/{organization_id}", response_model=ApiResponse)
def get_organization(
    organization_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = OrganizationRepository(db)

    try:
        org_id = uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid organization_id",
            details={"organization_id": organization_id},
        ) from exc

    org = repo.get_by_id(org_id)
    if org is None:
        raise NotFoundError(
            "Organization not found",
            details={"organization_id": organization_id},
        )

    return ApiResponse(
        data={
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "is_active": org.is_active,
        },
        meta={},
        error=None,
    )