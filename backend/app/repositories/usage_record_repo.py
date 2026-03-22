from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.usage_record import UsageRecord


class UsageRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, usage_record: UsageRecord) -> UsageRecord:
        self.db.add(usage_record)
        self.db.flush()
        self.db.refresh(usage_record)
        return usage_record

    def create_many(self, usage_records: list[UsageRecord]) -> list[UsageRecord]:
        self.db.add_all(usage_records)
        self.db.flush()
        for item in usage_records:
            self.db.refresh(item)
        return usage_records

    def get_by_id(self, usage_record_id: uuid.UUID) -> UsageRecord | None:
        stmt = select(UsageRecord).where(UsageRecord.id == usage_record_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        subscription_id: uuid.UUID | None = None,
        driver_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        usage_type: str | None = None,
        usage_date_from: date | None = None,
        usage_date_to: date | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[UsageRecord], int]:
        stmt = select(UsageRecord)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(UsageRecord)

        if organization_id is not None:
            stmt = stmt.where(UsageRecord.organization_id == organization_id)
            count_stmt = count_stmt.where(UsageRecord.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(UsageRecord.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                UsageRecord.customer_account_id == customer_account_id
            )

        if subscription_id is not None:
            stmt = stmt.where(UsageRecord.subscription_id == subscription_id)
            count_stmt = count_stmt.where(UsageRecord.subscription_id == subscription_id)

        if driver_id is not None:
            stmt = stmt.where(UsageRecord.driver_id == driver_id)
            count_stmt = count_stmt.where(UsageRecord.driver_id == driver_id)

        if load_id is not None:
            stmt = stmt.where(UsageRecord.load_id == load_id)
            count_stmt = count_stmt.where(UsageRecord.load_id == load_id)

        if usage_type:
            stmt = stmt.where(UsageRecord.usage_type == usage_type)
            count_stmt = count_stmt.where(UsageRecord.usage_type == usage_type)

        if usage_date_from is not None:
            stmt = stmt.where(UsageRecord.usage_date >= usage_date_from)
            count_stmt = count_stmt.where(UsageRecord.usage_date >= usage_date_from)

        if usage_date_to is not None:
            stmt = stmt.where(UsageRecord.usage_date <= usage_date_to)
            count_stmt = count_stmt.where(UsageRecord.usage_date <= usage_date_to)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(UsageRecord.usage_date.desc(), UsageRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, usage_record: UsageRecord) -> UsageRecord:
        self.db.add(usage_record)
        self.db.flush()
        self.db.refresh(usage_record)
        return usage_record

    def delete(self, usage_record: UsageRecord) -> None:
        self.db.delete(usage_record)
        self.db.flush()