from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
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
        gross_amount: Decimal | str | float | int | None = None,
        currency_code: str = "USD",
        notes: str | None = None,
    ) -> Load:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )
        normalized_driver_id = self._normalize_uuid(
            driver_id,
            field_name="driver_id",
        )

        load = Load(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
            driver_id=normalized_driver_id,
            broker_id=(
                self._normalize_uuid(broker_id, field_name="broker_id")
                if broker_id is not None and self._clean_text(broker_id) is not None
                else None
            ),
            source_channel=self._normalize_channel(source_channel),
            status=LoadStatus.BOOKED,
            processing_status=ProcessingStatus.PENDING,
            load_number=self._clean_text(load_number),
            rate_confirmation_number=self._clean_text(rate_confirmation_number),
            bol_number=self._clean_text(bol_number),
            invoice_number=self._clean_text(invoice_number),
            broker_name_raw=self._clean_text(broker_name_raw),
            broker_email_raw=self._normalize_email(broker_email_raw),
            pickup_date=self._normalize_date(
                pickup_date,
                field_name="pickup_date",
                allow_none=True,
            ),
            delivery_date=self._normalize_date(
                delivery_date,
                field_name="delivery_date",
                allow_none=True,
            ),
            pickup_location=self._clean_text(pickup_location),
            delivery_location=self._clean_text(delivery_location),
            gross_amount=self._normalize_decimal(gross_amount, field_name="gross_amount"),
            currency_code=self._normalize_currency(currency_code),
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
        normalized_load_id = self._require_text(load_id, field_name="load_id")
        load = self.load_repo.get_by_id(
            normalized_load_id,
            include_related=True,
        )
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": normalized_load_id})
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
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            status=normalized_status,
            source_channel=normalized_channel,
            date_from=self._normalize_date(
                date_from,
                field_name="date_from",
                allow_none=True,
            ),
            date_to=self._normalize_date(
                date_to,
                field_name="date_to",
                allow_none=True,
            ),
            search=self._clean_text(search),
            page=page,
            page_size=page_size,
            include_related=False,
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
            "follow_up_required",
            "next_follow_up_at",
            "follow_up_owner_id",
            "last_contacted_at",
            "notes",
            "status",
            "processing_status",
        }

        status_before = load.status

        for field, value in updates.items():
            if field not in allowed_updates:
                continue

            if field == "source_channel":
                if value is None:
                    continue
                setattr(load, field, self._normalize_channel(value))
            elif field == "status":
                if value is None:
                    continue
                setattr(load, field, self._normalize_load_status(value))
            elif field == "processing_status":
                if value is None:
                    continue
                setattr(load, field, self._normalize_processing_status(value))
            elif field in {"pickup_date", "delivery_date"}:
                setattr(
                    load,
                    field,
                    self._normalize_date(value, field_name=field, allow_none=True),
                )
            elif field in {
                "load_number",
                "rate_confirmation_number",
                "bol_number",
                "invoice_number",
                "broker_name_raw",
                "pickup_location",
                "delivery_location",
                "notes",
            }:
                setattr(load, field, self._clean_text(value))
            elif field == "broker_email_raw":
                setattr(load, field, self._normalize_email(value))
            elif field == "currency_code":
                if value is None:
                    continue
                setattr(load, field, self._normalize_currency(value))
            elif field == "gross_amount":
                setattr(load, field, self._normalize_decimal(value, field_name="gross_amount"))
            elif field in {"customer_account_id", "driver_id"}:
                if value is None:
                    continue
                setattr(load, field, self._normalize_uuid(value, field_name=field))
            elif field == "broker_id":
                if value is None or self._clean_text(value) is None:
                    setattr(load, field, None)
                else:
                    setattr(load, field, self._normalize_uuid(value, field_name="broker_id"))
            elif field in {
                "documents_complete",
                "has_ratecon",
                "has_bol",
                "has_invoice",
                "follow_up_required",
            }:
                setattr(load, field, bool(value))
            elif field == "next_follow_up_at":
                setattr(load, field, self._normalize_datetime(value, field_name=field, allow_none=True))
            elif field == "last_contacted_at":
                if value is None:
                    continue
                setattr(load, field, self._normalize_datetime(value, field_name=field, allow_none=True))
            elif field == "follow_up_owner_id":
                if value is None or self._clean_text(value) is None:
                    setattr(load, field, None)
                else:
                    setattr(load, field, self._normalize_uuid(value, field_name=field))
            else:
                setattr(load, field, value)

        load.documents_complete = bool(load.has_ratecon and load.has_invoice)

        if load.status != status_before:
            self._sync_status_timestamps(load, old_status=status_before, new_status=load.status)

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
            load.has_ratecon = bool(has_ratecon)
        if has_bol is not None:
            load.has_bol = bool(has_bol)
        if has_invoice is not None:
            load.has_invoice = bool(has_invoice)

        load.documents_complete = bool(load.has_ratecon and load.has_invoice)
        if load.documents_complete and load.status == LoadStatus.BOOKED:
            self._sync_status_timestamps(
                load,
                old_status=load.status,
                new_status=LoadStatus.DOCS_RECEIVED,
            )
            load.status = LoadStatus.DOCS_RECEIVED

        return self.load_repo.update(load)

    def update_extraction_confidence(
        self,
        *,
        load_id: str,
        extraction_confidence_avg: Any,
    ) -> Load:
        load = self.get_load(load_id)
        load.extraction_confidence_avg = self._normalize_decimal(
            extraction_confidence_avg,
            field_name="extraction_confidence_avg",
        )
        load.last_reviewed_at = datetime.now(timezone.utc)
        return self.load_repo.update(load)

    def _sync_status_timestamps(
        self,
        load: Load,
        *,
        old_status: LoadStatus,
        new_status: LoadStatus,
    ) -> None:
        _ = old_status
        now = datetime.now(timezone.utc)

        if new_status in {
            LoadStatus.SUBMITTED_TO_BROKER,
            LoadStatus.SUBMITTED_TO_FACTORING,
        } and load.submitted_at is None:
            load.submitted_at = now

        if new_status == LoadStatus.ADVANCE_PAID and load.funded_at is None:
            if load.submitted_at is None:
                load.submitted_at = now
            load.funded_at = now

        if new_status in {LoadStatus.FULLY_PAID, LoadStatus.SHORT_PAID} and load.paid_at is None:
            if load.submitted_at is None:
                load.submitted_at = now
            load.paid_at = now


    def _normalize_datetime(self, value: Any, *, field_name: str, allow_none: bool = False) -> datetime | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError(f"{field_name} is required", details={field_name: value})

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                if allow_none:
                    return None
                raise ValidationError(f"{field_name} is required", details={field_name: value})
            try:
                return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError(f"Invalid {field_name}", details={field_name: value}) from exc

        raise ValidationError(f"Invalid {field_name}", details={field_name: value})

    def _normalize_currency(self, value: Any) -> str:
        normalized = str(value or "USD").strip().upper()

        if len(normalized) != 3:
            raise ValidationError(
                "Invalid currency_code",
                details={"currency_code": value},
            )

        return normalized

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
            return None if allow_none else LoadStatus.BOOKED

        if isinstance(value, LoadStatus):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, LoadStatus] = {
            "new": LoadStatus.BOOKED,
            "needs_review": LoadStatus.DOCS_NEEDS_ATTENTION,
            "ready_to_submit": LoadStatus.INVOICE_READY,
            "waiting_on_broker": LoadStatus.SUBMITTED_TO_BROKER,
            "waiting_on_funding": LoadStatus.RESERVE_PENDING,
            "funded": LoadStatus.ADVANCE_PAID,
            "paid": LoadStatus.FULLY_PAID,
            "exception": LoadStatus.DOCS_NEEDS_ATTENTION,
        }
        if normalized in aliases:
            return aliases[normalized]

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
            if allow_none:
                return None
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

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

    def _normalize_decimal(self, value: Any, *, field_name: str) -> Decimal | None:
        if value is None or value == "":
            return None

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    def _normalize_uuid(self, value: Any, *, field_name: str) -> uuid.UUID:
        cleaned = self._require_text(value, field_name=field_name)
        try:
            return uuid.UUID(cleaned)
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    def _require_text(self, value: Any, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    def _normalize_email(self, value: Any) -> str | None:
        cleaned = self._clean_text(value)
        return cleaned.lower() if cleaned else None
