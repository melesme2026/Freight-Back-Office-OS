from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError
from app.domain.models.broker import Broker
from app.repositories.broker_repo import BrokerRepository
from app.schemas.common import ApiResponse


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


def _serialize_broker(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "name": item.name,
        "mc_number": item.mc_number,
        "email": item.email,
        "phone": item.phone,
        "payment_terms_days": item.payment_terms_days,
        "notes": item.notes,
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


def _get_broker_or_404(repo: BrokerRepository, broker_id: uuid.UUID) -> Broker:
    item = repo.get_by_id(broker_id)
    if item is None:
        raise NotFoundError(
            "Broker not found",
            details={"broker_id": str(broker_id)},
        )
    return item


@router.post("/brokers", response_model=ApiResponse)
def create_broker(
    *,
    organization_id: uuid.UUID,
    name: str,
    mc_number: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    payment_terms_days: int | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = BrokerRepository(db)

    item = Broker(
        organization_id=organization_id,
        name=name.strip(),
        mc_number=_normalize_optional_text(mc_number),
        email=_normalize_email(email),
        phone=_normalize_optional_text(phone),
        payment_terms_days=payment_terms_days,
        notes=notes,
    )
    created = repo.create(item)

    return ApiResponse(
        data=_serialize_broker(created),
        meta={},
        error=None,
    )


@router.get("/brokers", response_model=ApiResponse)
def list_brokers(
    *,
    organization_id: uuid.UUID | None = None,
    mc_number: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = BrokerRepository(db)
    items, total = repo.list(
        organization_id=organization_id,
        mc_number=_normalize_optional_text(mc_number),
        search=_normalize_optional_text(search),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_broker(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/brokers/{broker_id}", response_model=ApiResponse)
def get_broker(
    broker_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = BrokerRepository(db)
    item = _get_broker_or_404(repo, broker_id)

    return ApiResponse(
        data=_serialize_broker(item),
        meta={},
        error=None,
    )


@router.patch("/brokers/{broker_id}", response_model=ApiResponse)
def update_broker(
    broker_id: uuid.UUID,
    *,
    name: str | None = None,
    mc_number: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    payment_terms_days: int | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    repo = BrokerRepository(db)
    item = _get_broker_or_404(repo, broker_id)

    if name is not None:
        item.name = name.strip()
    if mc_number is not None:
        item.mc_number = _normalize_optional_text(mc_number)
    if email is not None:
        item.email = _normalize_email(email)
    if phone is not None:
        item.phone = _normalize_optional_text(phone)
    if payment_terms_days is not None:
        item.payment_terms_days = payment_terms_days
    if notes is not None:
        item.notes = notes

    updated = repo.update(item)

    return ApiResponse(
        data=_serialize_broker(updated),
        meta={},
        error=None,
    )