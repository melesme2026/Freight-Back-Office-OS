from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.payments.factoring_company_service import FactoringCompanyService

router = APIRouter(prefix="/factoring-companies")


class FactoringCompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    notes: str | None = None
    default_reserve_percent: str | None = None
    default_fee_percent: str | None = None


def _org_id(token_payload: dict[str, Any]) -> str:
    organization_id = token_payload.get("organization_id")
    if not organization_id:
        raise UnauthorizedError("Missing organization_id")
    return str(organization_id)


def _authorize_write(token_payload: dict[str, Any]) -> None:
    if str(token_payload.get("role") or "").strip().lower() == "driver":
        raise ForbiddenError("Driver accounts cannot modify factoring operations")


def _decimal_to_string(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, TypeError, ValueError):
        return str(value)


def _datetime_to_iso(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else str(value)


def _serialize(company: Any) -> dict[str, Any]:
    return {
        "id": str(company.id),
        "organization_id": str(company.organization_id),
        "company_name": company.company_name,
        "contact_email": company.contact_email,
        "phone": company.phone,
        "notes": company.notes,
        "default_reserve_percent": _decimal_to_string(company.default_reserve_percent),
        "default_fee_percent": _decimal_to_string(company.default_fee_percent),
        "created_at": _datetime_to_iso(company.created_at),
        "updated_at": _datetime_to_iso(company.updated_at),
    }


@router.get("", response_model=ApiResponse)
def list_factoring_companies(token_payload: dict[str, Any] = Depends(get_current_token_payload), db: Session = Depends(get_db_session)) -> ApiResponse:
    service = FactoringCompanyService(db)
    return ApiResponse(data=[_serialize(item) for item in service.list_companies(organization_id=_org_id(token_payload))], meta={}, error=None)


@router.post("", response_model=ApiResponse)
def create_factoring_company(payload: FactoringCompanyRequest, token_payload: dict[str, Any] = Depends(get_current_token_payload), db: Session = Depends(get_db_session)) -> ApiResponse:
    _authorize_write(token_payload)
    service = FactoringCompanyService(db)
    company = service.create_company(
        organization_id=_org_id(token_payload),
        company_name=payload.company_name or "",
        contact_email=payload.contact_email,
        phone=payload.phone,
        notes=payload.notes,
        default_reserve_percent=payload.default_reserve_percent,
        default_fee_percent=payload.default_fee_percent,
    )
    return ApiResponse(data=_serialize(company), meta={}, error=None)


@router.patch("/{company_id}", response_model=ApiResponse)
def update_factoring_company(company_id: uuid.UUID, payload: FactoringCompanyRequest, token_payload: dict[str, Any] = Depends(get_current_token_payload), db: Session = Depends(get_db_session)) -> ApiResponse:
    _authorize_write(token_payload)
    service = FactoringCompanyService(db)
    company = service.update_company(company_id=str(company_id), organization_id=_org_id(token_payload), **payload.model_dump(exclude_unset=True))
    return ApiResponse(data=_serialize(company), meta={}, error=None)
