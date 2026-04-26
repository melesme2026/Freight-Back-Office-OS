from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.domain.models.carrier_profile import CarrierProfile
from app.repositories.carrier_profile_repo import CarrierProfileRepository


class CarrierProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CarrierProfileRepository(db)

    def get_by_org(self, org_id: str | uuid.UUID) -> CarrierProfile | None:
        return self.repo.get_by_organization_id(org_id)

    def upsert_profile(self, org_id: str | uuid.UUID, data: dict[str, object]) -> CarrierProfile:
        normalized_org_id = uuid.UUID(str(org_id))
        existing = self.repo.get_by_organization_id(normalized_org_id)

        required_fields = [
            "legal_name",
            "address_line1",
            "city",
            "state",
            "zip",
            "phone",
            "email",
            "remit_to_name",
            "remit_to_address",
        ]

        for field in required_fields:
            value = data.get(field)
            if value is None or not str(value).strip():
                raise ValidationError(
                    f"{field} is required",
                    details={field: value},
                )

        normalized_data = {
            "legal_name": str(data.get("legal_name")).strip(),
            "address_line1": str(data.get("address_line1")).strip(),
            "address_line2": self._optional_text(data.get("address_line2")),
            "city": str(data.get("city")).strip(),
            "state": str(data.get("state")).strip(),
            "zip": str(data.get("zip")).strip(),
            "country": self._optional_text(data.get("country")) or "USA",
            "phone": str(data.get("phone")).strip(),
            "email": str(data.get("email")).strip().lower(),
            "mc_number": self._optional_text(data.get("mc_number")),
            "dot_number": self._optional_text(data.get("dot_number")),
            "remit_to_name": str(data.get("remit_to_name")).strip(),
            "remit_to_address": str(data.get("remit_to_address")).strip(),
            "remit_to_notes": self._optional_text(data.get("remit_to_notes")),
        }

        if existing is None:
            return self.repo.create(
                CarrierProfile(
                    organization_id=normalized_org_id,
                    **normalized_data,
                )
            )

        for key, value in normalized_data.items():
            setattr(existing, key, value)

        return self.repo.update(existing)

    @staticmethod
    def _optional_text(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
