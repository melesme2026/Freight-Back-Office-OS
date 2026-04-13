from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.domain.models.driver import Driver
from app.repositories.driver_repo import DriverRepository
from app.schemas.common import ApiResponse
from app.core.security import get_current_token_payload


router = APIRouter()


class DriverCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    full_name: str
    phone: str
    customer_account_id: uuid.UUID | None = None
    email: str | None = None
    is_active: bool = True


class DriverUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_account_id: uuid.UUID | None = None
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None


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


def _serialize_driver(item: Any) -> dict[str, Any]:
    customer_account = getattr(item, "customer_account", None)

    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": (
            str(item.customer_account_id) if item.customer_account_id else None
        ),
        "customer_account_name": (
            getattr(customer_account, "account_name", None) if customer_account else None
        ),
        "full_name": item.full_name,
        "phone": item.phone,
        "email": item.email,
        "is_active": item.is_active,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_driver_or_404(repo: DriverRepository, driver_id: uuid.UUID) -> Driver:
    item = repo.get_by_id(driver_id, include_related=True)
    if item is None:
        raise NotFoundError(
            "Driver not found",
            details={"driver_id": str(driver_id)},
        )
    return item


@router.post("/drivers", response_model=ApiResponse)
def create_driver(
    payload: DriverCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = DriverRepository(db)

    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    item = Driver(
        organization_id=payload.organization_id,
        customer_account_id=payload.customer_account_id,
        full_name=_normalize_required_text(payload.full_name, field_name="full_name"),
        phone=_normalize_required_text(payload.phone, field_name="phone"),
        email=_normalize_email(payload.email),
        is_active=payload.is_active,
    )
    created = repo.create(item)
    created = repo.get_by_id(created.id, include_related=True) or created

    return ApiResponse(
        data=_serialize_driver(created),
        meta={},
        error=None,
    )


@router.get("/drivers", response_model=ApiResponse)
def list_drivers(
    *,
    organization_id: uuid.UUID | None = None,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    customer_account_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = DriverRepository(db)
    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    items, total = repo.list(
        organization_id=effective_org_id,
        customer_account_id=customer_account_id,
        is_active=is_active,
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
        include_related=True,
    )

    return ApiResponse(
        data=[_serialize_driver(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/drivers/{driver_id}", response_model=ApiResponse)
def get_driver(
    driver_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = DriverRepository(db)
    item = _get_driver_or_404(repo, driver_id)
    token_org_id = token_payload.get("organization_id")
    if str(item.organization_id) != str(token_org_id):
        raise UnauthorizedError("Driver is not in authenticated organization")

    return ApiResponse(
        data=_serialize_driver(item),
        meta={},
        error=None,
    )


@router.patch("/drivers/{driver_id}", response_model=ApiResponse)
def update_driver(
    driver_id: uuid.UUID,
    payload: DriverUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = DriverRepository(db)
    item = _get_driver_or_404(repo, driver_id)

    if payload.customer_account_id is not None:
        item.customer_account_id = payload.customer_account_id
    if payload.full_name is not None:
        item.full_name = _normalize_required_text(payload.full_name, field_name="full_name")
    if payload.phone is not None:
        item.phone = _normalize_required_text(payload.phone, field_name="phone")
    if payload.email is not None:
        item.email = _normalize_email(payload.email)
    if payload.is_active is not None:
        item.is_active = payload.is_active

    updated = repo.update(item)
    updated = repo.get_by_id(updated.id, include_related=True) or updated

    return ApiResponse(
        data=_serialize_driver(updated),
        meta={},
        error=None,
    )