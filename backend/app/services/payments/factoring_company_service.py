from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.models.factoring_company import FactoringCompany
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class FactoringCompanyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_companies(self, *, organization_id: str) -> list[FactoringCompany]:
        stmt = (
            select(FactoringCompany)
            .where(FactoringCompany.organization_id == uuid.UUID(str(organization_id)))
            .order_by(func.lower(FactoringCompany.company_name))
        )
        return list(self.db.scalars(stmt).all())

    def get_company(self, *, company_id: str, organization_id: str) -> FactoringCompany:
        stmt = select(FactoringCompany).where(
            FactoringCompany.id == uuid.UUID(str(company_id)),
            FactoringCompany.organization_id == uuid.UUID(str(organization_id)),
        )
        company = self.db.scalar(stmt)
        if company is None:
            raise NotFoundError("Factoring company not found", details={"company_id": company_id})
        return company

    def create_company(
        self,
        *,
        organization_id: str,
        company_name: str,
        contact_email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        default_reserve_percent: str | Decimal | int | float | None = None,
        default_fee_percent: str | Decimal | int | float | None = None,
    ) -> FactoringCompany:
        company = FactoringCompany(
            organization_id=uuid.UUID(str(organization_id)),
            company_name=self._required_text(company_name, "company_name"),
            contact_email=self._clean(contact_email),
            phone=self._clean(phone),
            notes=self._clean(notes),
            default_reserve_percent=self._percent(default_reserve_percent),
            default_fee_percent=self._percent(default_fee_percent),
        )
        self.db.add(company)
        self.db.flush()
        return company

    def update_company(
        self, *, company_id: str, organization_id: str, **values: object
    ) -> FactoringCompany:
        company = self.get_company(company_id=company_id, organization_id=organization_id)
        if "company_name" in values and values["company_name"] is not None:
            company.company_name = self._required_text(str(values["company_name"]), "company_name")
        for field in ("contact_email", "phone", "notes"):
            if field in values:
                setattr(
                    company,
                    field,
                    self._clean(values[field] if isinstance(values[field], str) else None),
                )
        if "default_reserve_percent" in values and values["default_reserve_percent"] is not None:
            company.default_reserve_percent = self._percent(values["default_reserve_percent"])
        if "default_fee_percent" in values and values["default_fee_percent"] is not None:
            company.default_fee_percent = self._percent(values["default_fee_percent"])
        self.db.flush()
        return company

    def _required_text(self, value: str | None, field_name: str) -> str:
        normalized = self._clean(value)
        if not normalized:
            raise ValidationError(f"{field_name} is required")
        return normalized

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _percent(self, value: object) -> Decimal:
        if value is None or value == "":
            return Decimal("0")
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("Percent must be a valid number") from exc
        if amount < Decimal("0") or amount > Decimal("100"):
            raise ValidationError("Percent must be between 0 and 100")
        return amount
