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
from app.schemas.common import ApiResponse
from app.services.carrier_profile_service import CarrierProfileService


router = APIRouter()


class CarrierProfileUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    zip: str
    country: str | None = "USA"
    phone: str
    email: str
    mc_number: str | None = None
    dot_number: str | None = None
    remit_to_name: str
    remit_to_address: str
    remit_to_notes: str | None = None


class CarrierProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    mc_number: str | None = None
    dot_number: str | None = None
    remit_to_name: str | None = None
    remit_to_address: str | None = None
    remit_to_notes: str | None = None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _assert_org_scope(token_payload: dict[str, Any]) -> uuid.UUID:
    token_org_id = str(token_payload.get("organization_id") or "").strip()
    if not token_org_id:
        raise UnauthorizedError("Token organization_id is missing")
    return uuid.UUID(token_org_id)


def _assert_can_update(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in {"owner", "admin"}:
        raise UnauthorizedError("Only owner/admin can update carrier profile")


def _serialize(profile: Any) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "organization_id": str(profile.organization_id),
        "legal_name": profile.legal_name,
        "address_line1": profile.address_line1,
        "address_line2": profile.address_line2,
        "city": profile.city,
        "state": profile.state,
        "zip": profile.zip,
        "country": profile.country,
        "phone": profile.phone,
        "email": profile.email,
        "mc_number": profile.mc_number,
        "dot_number": profile.dot_number,
        "remit_to_name": profile.remit_to_name,
        "remit_to_address": profile.remit_to_address,
        "remit_to_notes": profile.remit_to_notes,
        "created_at": _to_iso_or_none(profile.created_at),
        "updated_at": _to_iso_or_none(profile.updated_at),
    }


@router.get("/carrier-profile", response_model=ApiResponse)
def get_carrier_profile(
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    org_id = _assert_org_scope(token_payload)
    service = CarrierProfileService(db)
    profile = service.get_by_org(org_id)
    if profile is None:
        raise NotFoundError("Carrier profile not found", details={"organization_id": str(org_id)})
    return ApiResponse(data=_serialize(profile), meta={}, error=None)


@router.post("/carrier-profile", response_model=ApiResponse)
def create_carrier_profile(
    payload: CarrierProfileUpsertRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_can_update(token_payload)
    org_id = _assert_org_scope(token_payload)
    service = CarrierProfileService(db)

    existing = service.get_by_org(org_id)
    if existing is not None:
        raise ValidationError("Carrier profile already exists", details={"organization_id": str(org_id)})

    profile = service.upsert_profile(org_id, payload.model_dump())
    db.commit()
    return ApiResponse(data=_serialize(profile), meta={}, error=None)


@router.patch("/carrier-profile", response_model=ApiResponse)
def update_carrier_profile(
    payload: CarrierProfilePatchRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _assert_can_update(token_payload)
    org_id = _assert_org_scope(token_payload)
    service = CarrierProfileService(db)
    existing = service.get_by_org(org_id)
    if existing is None:
        raise NotFoundError("Carrier profile not found", details={"organization_id": str(org_id)})

    updates = payload.model_dump(exclude_unset=True)
    base_data = _serialize(existing)
    merged = {
        "legal_name": updates.get("legal_name", base_data["legal_name"]),
        "address_line1": updates.get("address_line1", base_data["address_line1"]),
        "address_line2": updates.get("address_line2", base_data["address_line2"]),
        "city": updates.get("city", base_data["city"]),
        "state": updates.get("state", base_data["state"]),
        "zip": updates.get("zip", base_data["zip"]),
        "country": updates.get("country", base_data["country"]),
        "phone": updates.get("phone", base_data["phone"]),
        "email": updates.get("email", base_data["email"]),
        "mc_number": updates.get("mc_number", base_data["mc_number"]),
        "dot_number": updates.get("dot_number", base_data["dot_number"]),
        "remit_to_name": updates.get("remit_to_name", base_data["remit_to_name"]),
        "remit_to_address": updates.get("remit_to_address", base_data["remit_to_address"]),
        "remit_to_notes": updates.get("remit_to_notes", base_data["remit_to_notes"]),
    }

    profile = service.upsert_profile(org_id, merged)
    db.commit()
    return ApiResponse(data=_serialize(profile), meta={}, error=None)
