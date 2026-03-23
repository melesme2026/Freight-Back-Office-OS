from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load import Load
from app.repositories.load_repo import LoadRepository


class LoadService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)

    def create_load(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        driver_id: str,
        broker_id: str | None = None,
        source_channel: str = Channel.MANUAL,
        load_number: str | None = None,
        rate_confirmation_number: str | None = None,
        bol_number: str | None = None,
        invoice_number: str | None = None,
        broker_name_raw: str | None = None,
        broker_email_raw: str | None = None,
        pickup_date: Any = None,
        delivery_date: Any = None,
        pickup_location: str | None = None,
        delivery_location: str | None = None,
        gross_amount: Decimal | None = None,
        currency_code: str = "USD",
        notes: str | None = None,
    ) -> Load:
        load = Load(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            broker_id=broker_id,
            source_channel=source_channel,
            status=LoadStatus.NEW,
            processing_status=ProcessingStatus.PENDING,
            load_number=load_number,
            rate_confirmation_number=rate_confirmation_number,
            bol_number=bol_number,
            invoice_number=invoice_number,
            broker_name_raw=broker_name_raw,
            broker_email_raw=broker_email_raw,
            pickup_date=pickup_date,
            delivery_date=delivery_date,
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            gross_amount=gross_amount,
            currency_code=currency_code,
            documents_complete=False,
            has_ratecon=False,
            has_bol=False,
            has_invoice=False,
            extraction_confidence_avg=None,
            last_reviewed_by=None,
            last_reviewed_at=None,
            submitted_at=None,
            funded_at=None,
            paid_at=None,
            notes=notes,
        )
        return self.load_repo.create(load)

    def get_load(self, load_id: str) -> Load:
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def list_loads(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        status: str | None = None,
        source_channel: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Load], int]:
        return self.load_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            status=status,
            source_channel=source_channel,
            date_from=date_from,
            date_to=date_to,
            search=search,
            page=page,
            page_size=page_size,
        )

    def update_load(
        self,
        *,
        load_id: str,
        **updates: Any,
    ) -> Load:
        load = self.get_load(load_id)

        for field, value in updates.items():
            if hasattr(load, field) and value is not None:
                setattr(load, field, value)

        return self.load_repo.update(load)

    def attach_document_flags(
        self,
        *,
        load_id: str,
        has_ratecon: bool | None = None,
        has_bol: bool | None = None,
        has_invoice: bool | None = None,
    ) -> Load:
        load = self.get_load(load_id)

        if has_ratecon is not None:
            load.has_ratecon = has_ratecon
        if has_bol is not None:
            load.has_bol = has_bol
        if has_invoice is not None:
            load.has_invoice = has_invoice

        load.documents_complete = bool(load.has_ratecon and load.has_bol)

        if load.documents_complete and load.status == LoadStatus.NEW:
            load.status = LoadStatus.DOCS_RECEIVED

        return self.load_repo.update(load)

    def update_extraction_confidence(
        self,
        *,
        load_id: str,
        extraction_confidence_avg: Decimal | None,
    ) -> Load:
        load = self.get_load(load_id)
        load.extraction_confidence_avg = extraction_confidence_avg
        load.last_reviewed_at = datetime.now(timezone.utc)
        return self.load_repo.update(load)