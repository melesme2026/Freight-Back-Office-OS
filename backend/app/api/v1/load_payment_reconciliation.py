from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService

router = APIRouter(prefix="/loads/{load_id}/payment-reconciliation")


class PaymentPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_received: str | None = None
    notes: str | None = None
    factor_name: str | None = None
    factoring_used: bool | None = None


class MarkPaidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str
    paid_date: datetime | None = None


class MarkPartialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str


class MarkAdvanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str
    advance_date: datetime | None = None
    factor_name: str | None = None


class MarkReservePendingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reserve_amount: str


class MarkReservePaidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: str
    reserve_paid_date: datetime | None = None


class MarkShortPaidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received_amount: str
    expected_amount: str
    reason: str | None = None


class MarkDisputedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


def _to_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _serialize(record: Any) -> dict[str, Any]:
    return {
        "id": _to_str(getattr(record, "id", None)),
        "organization_id": _to_str(getattr(record, "organization_id", None)),
        "load_id": _to_str(getattr(record, "load_id", None)),
        "gross_amount": str(_to_decimal(getattr(record, "gross_amount", 0))),
        "expected_amount": str(_to_decimal(getattr(record, "expected_amount", 0))),
        "amount_received": str(_to_decimal(getattr(record, "amount_received", 0))),
        "currency": getattr(record, "currency", "USD"),
        "payment_status": getattr(getattr(record, "payment_status", None), "value", getattr(record, "payment_status", None)),
        "paid_date": getattr(record, "paid_date", None).isoformat() if getattr(record, "paid_date", None) else None,
        "factoring_used": bool(getattr(record, "factoring_used", False)),
        "factor_name": getattr(record, "factor_name", None),
        "advance_amount": str(_to_decimal(getattr(record, "advance_amount", 0))) if getattr(record, "advance_amount", None) is not None else None,
        "advance_date": getattr(record, "advance_date", None).isoformat() if getattr(record, "advance_date", None) else None,
        "factoring_fee_amount": str(_to_decimal(getattr(record, "factoring_fee_amount", 0))) if getattr(record, "factoring_fee_amount", None) is not None else None,
        "reserve_amount": str(_to_decimal(getattr(record, "reserve_amount", 0))) if getattr(record, "reserve_amount", None) is not None else None,
        "reserve_paid_amount": str(_to_decimal(getattr(record, "reserve_paid_amount", 0))),
        "reserve_paid_date": getattr(record, "reserve_paid_date", None).isoformat() if getattr(record, "reserve_paid_date", None) else None,
        "deduction_amount": str(_to_decimal(getattr(record, "deduction_amount", 0))) if getattr(record, "deduction_amount", None) is not None else None,
        "short_paid_amount": str(_to_decimal(getattr(record, "short_paid_amount", 0))) if getattr(record, "short_paid_amount", None) is not None else None,
        "dispute_reason": getattr(record, "dispute_reason", None),
        "notes": getattr(record, "notes", None),
        "created_by_staff_user_id": _to_str(getattr(record, "created_by_staff_user_id", None)),
        "updated_by_staff_user_id": _to_str(getattr(record, "updated_by_staff_user_id", None)),
        "created_at": getattr(record, "created_at", None).isoformat() if getattr(record, "created_at", None) else None,
        "updated_at": getattr(record, "updated_at", None).isoformat() if getattr(record, "updated_at", None) else None,
    }


def _authorize_payment_read(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").lower()
    if role in {"owner", "admin", "ops", "ops_manager", "ops_agent", "billing", "billing_admin", "support", "support_agent", "viewer", "driver"}:
        return
    raise ForbiddenError("You do not have permission to view payment reconciliation")


def _authorize_payment_write(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").lower()
    if role in {"owner", "admin", "ops", "ops_manager", "ops_agent", "billing", "billing_admin"}:
        return
    raise ForbiddenError("You do not have permission to modify payment reconciliation")


def _actor_id(token_payload: dict[str, Any]) -> str | None:
    for key in ("staff_user_id", "sub"):
        value = token_payload.get(key)
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return None


def _service(db: Session) -> PaymentReconciliationService:
    return PaymentReconciliationService(db)


def _org_id(token_payload: dict[str, Any]) -> str:
    return str(token_payload.get("organization_id") or "")


@router.get("/", response_model=ApiResponse)
def get_payment_reconciliation(
    load_id: str,
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_payment_read(token_payload)
    service = _service(db)
    record = service.get_or_create_for_load(load_id, _org_id(token_payload), actor_staff_user_id=_actor_id(token_payload))
    return ApiResponse(data=_serialize(record))


@router.patch("/", response_model=ApiResponse)
def patch_payment_reconciliation(
    load_id: str,
    payload: PaymentPatchRequest,
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.get_or_create_for_load(load_id, _org_id(token_payload), actor_staff_user_id=_actor_id(token_payload))

    if payload.amount_received is not None:
        record = service.update_amount_received(load_id, _org_id(token_payload), payload.amount_received)
    if payload.notes is not None:
        record.notes = payload.notes.strip() or None
    if payload.factor_name is not None:
        record.factor_name = payload.factor_name.strip() or None
    if payload.factoring_used is not None:
        record.factoring_used = payload.factoring_used
    record.payment_status = service.compute_status(record)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-paid", response_model=ApiResponse)
def mark_paid(load_id: str, payload: MarkPaidRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_paid(load_id, _org_id(token_payload), payload.amount, payload.paid_date)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-partial-payment", response_model=ApiResponse)
def mark_partial_payment(load_id: str, payload: MarkPartialRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_partial_payment(load_id, _org_id(token_payload), payload.amount)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-advance-paid", response_model=ApiResponse)
def mark_advance_paid(load_id: str, payload: MarkAdvanceRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_advance_paid(load_id, _org_id(token_payload), payload.amount, payload.advance_date, payload.factor_name)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-reserve-pending", response_model=ApiResponse)
def mark_reserve_pending(load_id: str, payload: MarkReservePendingRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_reserve_pending(load_id, _org_id(token_payload), payload.reserve_amount)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-reserve-paid", response_model=ApiResponse)
def mark_reserve_paid(load_id: str, payload: MarkReservePaidRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_reserve_paid(load_id, _org_id(token_payload), payload.amount, payload.reserve_paid_date)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-short-paid", response_model=ApiResponse)
def mark_short_paid(load_id: str, payload: MarkShortPaidRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_short_paid(
        load_id,
        _org_id(token_payload),
        payload.received_amount,
        payload.expected_amount,
        payload.reason,
    )
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))


@router.post("/mark-disputed", response_model=ApiResponse)
def mark_disputed(load_id: str, payload: MarkDisputedRequest, db: Session = Depends(get_db_session), token_payload: dict[str, Any] = Depends(get_current_token_payload)) -> ApiResponse:
    _authorize_payment_write(token_payload)
    service = _service(db)
    record = service.mark_disputed(load_id, _org_id(token_payload), payload.reason)
    record.updated_by_staff_user_id = uuid.UUID(_actor_id(token_payload)) if _actor_id(token_payload) else None
    db.flush()
    return ApiResponse(data=_serialize(record))
