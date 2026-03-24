from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
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
        source_channel: str | Channel = Channel.MANUAL,
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
            source_channel=self._normalize_channel(source_channel),
            status=LoadStatus.NEW,
            processing_status=ProcessingStatus.PENDING,
            load_number=self._clean_text(load_number),
            rate_confirmation_number=self._clean_text(rate_confirmation_number),
            bol_number=self._clean_text(bol_number),
            invoice_number=self._clean_text(invoice_number),
            broker_name_raw=self._clean_text(broker_name_raw),
            broker_email_raw=self._clean_text(broker_email_raw),
            pickup_date=self._normalize_date(pickup_date, field_name="pickup_date"),
            delivery_date=self._normalize_date(delivery_date, field_name="delivery_date"),
            pickup_location=self._clean_text(pickup_location),
            delivery_location=self._clean_text(delivery_location),
            gross_amount=gross_amount,
            currency_code=(currency_code or "USD").strip().upper(),
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
            notes=self._clean_text(notes),
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
        status: str | LoadStatus | None = None,
        source_channel: str | Channel | None = None,
        date_from: Any = None,
        date_to: Any = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Load], int]:
        normalized_status = self._normalize_load_status(status, allow_none=True)
        normalized_channel = self._normalize_channel(source_channel, allow_none=True)

        return self.load_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            status=normalized_status,
            source_channel=normalized_channel,
            date_from=self._normalize_date(date_from, field_name="date_from", allow_none=True),
            date_to=self._normalize_date(date_to, field_name="date_to", allow_none=True),
            search=self._clean_text(search),
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

        allowed_updates = {
            "customer_account_id",
            "driver_id",
            "broker_id",
            "source_channel",
            "load_number",
            "rate_confirmation_number",
            "bol_number",
            "invoice_number",
            "broker_name_raw",
            "broker_email_raw",
            "pickup_date",
            "delivery_date",
            "pickup_location",
            "delivery_location",
            "gross_amount",
            "currency_code",
            "documents_complete",
            "has_ratecon",
            "has_bol",
            "has_invoice",
            "notes",
            "status",
            "processing_status",
        }

        for field, value in updates.items():
            if field not in allowed_updates or value is None:
                continue

            if field == "source_channel":
                setattr(load, field, self._normalize_channel(value))
            elif field == "status":
                setattr(load, field, self._normalize_load_status(value))
            elif field == "processing_status":
                setattr(load, field, self._normalize_processing_status(value))
            elif field in {"pickup_date", "delivery_date"}:
                setattr(load, field, self._normalize_date(value, field_name=field))
            elif field in {
                "load_number",
                "rate_confirmation_number",
                "bol_number",
                "invoice_number",
                "broker_name_raw",
                "broker_email_raw",
                "pickup_location",
                "delivery_location",
                "notes",
            }:
                setattr(load, field, self._clean_text(value))
            elif field == "currency_code":
                setattr(load, field, str(value).strip().upper())
            else:
                setattr(load, field, value)

        if any(
            key in updates
            for key in {"has_ratecon", "has_bol", "has_invoice", "documents_complete"}
        ):
            load.documents_complete = bool(load.has_ratecon and load.has_bol and load.has_invoice)

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

        load.documents_complete = bool(load.has_ratecon and load.has_bol and load.has_invoice)

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

    def _normalize_channel(
        self,
        value: str | Channel | None,
        *,
        allow_none: bool = False,
    ) -> Channel | None:
        if value is None:
            return None if allow_none else Channel.MANUAL

        if isinstance(value, Channel):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, Channel] = {
            "web": Channel.WEB,
            "whatsapp": Channel.WHATSAPP,
            "email": Channel.EMAIL,
            "api": Channel.API,
            "manual": Channel.MANUAL,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid source_channel",
            details={"source_channel": value},
        )

    def _normalize_load_status(
        self,
        value: str | LoadStatus | None,
        *,
        allow_none: bool = False,
    ) -> LoadStatus | None:
        if value is None:
            return None if allow_none else LoadStatus.NEW

        if isinstance(value, LoadStatus):
            return value

        normalized = str(value).strip().lower()

        for status in LoadStatus:
            if normalized == str(status).lower():
                return status
            if normalized == getattr(status, "value", "").lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValidationError(
            "Invalid status",
            details={"status": value},
        )

    def _normalize_processing_status(
        self,
        value: str | ProcessingStatus | None,
    ) -> ProcessingStatus:
        if value is None:
            raise ValidationError(
                "processing_status is required",
                details={"processing_status": value},
            )

        if isinstance(value, ProcessingStatus):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, ProcessingStatus] = {
            "pending": ProcessingStatus.PENDING,
            "not_started": ProcessingStatus.PENDING,
            "processing": ProcessingStatus.IN_PROGRESS,
            "in_progress": ProcessingStatus.IN_PROGRESS,
            "inprogress": ProcessingStatus.IN_PROGRESS,
            "completed": ProcessingStatus.COMPLETED,
            "complete": ProcessingStatus.COMPLETED,
            "failed": ProcessingStatus.FAILED,
            "error": ProcessingStatus.FAILED,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid processing_status",
            details={"processing_status": value},
        )

    def _normalize_date(
        self,
        value: Any,
        *,
        field_name: str,
        allow_none: bool = False,
    ) -> date | None:
        if value is None or value == "":
            return None if allow_none else None

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        try:
            return date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None