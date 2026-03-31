from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.models.usage_record import UsageRecord
from app.repositories.usage_record_repo import UsageRecordRepository


class UsageBillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usage_record_repo = UsageRecordRepository(db)

    def record_usage(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        subscription_id: str,
        usage_type: str,
        quantity: Decimal,
        usage_date: date,
        driver_id: str | None = None,
        load_id: str | None = None,
        unit_price: Decimal | None = None,
        metadata_json: dict | list | None = None,
    ) -> UsageRecord:
        normalized_quantity = Decimal(str(quantity))
        normalized_unit_price = Decimal(str(unit_price)) if unit_price is not None else None

        usage_record = UsageRecord(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            subscription_id=subscription_id,
            driver_id=driver_id,
            load_id=load_id,
            usage_type=usage_type,
            quantity=normalized_quantity,
            unit_price=normalized_unit_price,
            usage_date=usage_date,
            metadata_json=metadata_json,
        )
        return self.usage_record_repo.create(usage_record)

    def list_usage(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        subscription_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        usage_type: str | None = None,
        usage_date_from: date | None = None,
        usage_date_to: date | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[UsageRecord], int]:
        return self.usage_record_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            subscription_id=subscription_id,
            driver_id=driver_id,
            load_id=load_id,
            usage_type=usage_type,
            usage_date_from=usage_date_from,
            usage_date_to=usage_date_to,
            page=page,
            page_size=page_size,
        )

    def calculate_usage_total(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        subscription_id: str | None = None,
        usage_date_from: date | None = None,
        usage_date_to: date | None = None,
    ) -> Decimal:
        records, _ = self.usage_record_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            subscription_id=subscription_id,
            usage_date_from=usage_date_from,
            usage_date_to=usage_date_to,
            page=1,
            page_size=10000,
        )

        total = Decimal("0.00")
        for record in records:
            if record.unit_price is None:
                continue
            total += Decimal(str(record.quantity)) * Decimal(str(record.unit_price))

        return total.quantize(Decimal("0.01"))