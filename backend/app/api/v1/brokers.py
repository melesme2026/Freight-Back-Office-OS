from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.broker import Broker
from app.repositories.broker_repo import BrokerRepository
from app.schemas.common import ApiResponse


router = APIRouter()


@router.post("/brokers", response_model=ApiResponse)
def create_broker(
    *,
    organization_id: str,
    name: str,
    mc_number: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    payment_terms_days: int | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_organization_id = uuid.UUID(organization_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid organization_id",
            details={"organization_id": organization_id},
        ) from exc

    repo = BrokerRepository(db)

    item = Broker(
        organization_id=parsed_organization_id,
        name=name.strip(),
        mc_number=mc_number.strip() if mc_number else None,
        email=email.strip().lower() if email else None,
        phone=phone.strip() if phone else None,
        payment_terms_days=payment_terms_days,
        notes=notes,
    )
    created = repo.create(item)

    return ApiResponse(
        data={
            "id": str(created.id),
            "organization_id": str(created.organization_id),
            "name": created.name,
            "mc_number": created.mc_number,
            "email": created.email,
            "phone": created.phone,
            "payment_terms_days": created.payment_terms_days,
            "notes": created.notes,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/brokers", response_model=ApiResponse)
def list_brokers(
    *,
    organization_id: str | None = None,
    mc_number: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    parsed_organization_id = None
    if organization_id:
        try:
            parsed_organization_id = uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    repo = BrokerRepository(db)
    items, total = repo.list(
        organization_id=parsed_organization_id,
        mc_number=mc_number,
        search=search,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "name": item.name,
                "mc_number": item.mc_number,
                "email": item.email,
                "phone": item.phone,
                "payment_terms_days": item.payment_terms_days,
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


@router.get("/brokers/{broker_id}", response_model=ApiResponse)
def get_broker(
    broker_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_broker_id = uuid.UUID(broker_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid broker_id",
            details={"broker_id": broker_id},
        ) from exc

    repo = BrokerRepository(db)
    item = repo.get_by_id(parsed_broker_id)
    if item is None:
        raise NotFoundError(
            "Broker not found",
            details={"broker_id": broker_id},
        )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "name": item.name,
            "mc_number": item.mc_number,
            "email": item.email,
            "phone": item.phone,
            "payment_terms_days": item.payment_terms_days,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.patch("/brokers/{broker_id}", response_model=ApiResponse)
def update_broker(
    broker_id: str,
    *,
    name: str | None = None,
    mc_number: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    payment_terms_days: int | None = None,
    notes: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        parsed_broker_id = uuid.UUID(broker_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid broker_id",
            details={"broker_id": broker_id},
        ) from exc

    repo = BrokerRepository(db)
    item = repo.get_by_id(parsed_broker_id)
    if item is None:
        raise NotFoundError(
            "Broker not found",
            details={"broker_id": broker_id},
        )

    if name is not None:
        item.name = name.strip()
    if mc_number is not None:
        item.mc_number = mc_number.strip() if mc_number else None
    if email is not None:
        item.email = email.strip().lower() if email else None
    if phone is not None:
        item.phone = phone.strip() if phone else None
    if payment_terms_days is not None:
        item.payment_terms_days = payment_terms_days
    if notes is not None:
        item.notes = notes

    updated = repo.update(item)

    return ApiResponse(
        data={
            "id": str(updated.id),
            "organization_id": str(updated.organization_id),
            "name": updated.name,
            "mc_number": updated.mc_number,
            "email": updated.email,
            "phone": updated.phone,
            "payment_terms_days": updated.payment_terms_days,
            "notes": updated.notes,
            "created_at": updated.created_at.isoformat(),
            "updated_at": updated.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )