from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.billing.billing_service import BillingService


router = APIRouter()


def _to_decimal_string(value: object | None) -> str | None:
    """
    Normalize numeric dashboard values to string form for consistent API output.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return format(value, "f")

    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


@router.get("/billing/dashboard", response_model=ApiResponse)
def get_billing_dashboard(
    *,
    organization_id: uuid.UUID | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = BillingService(db)
    data = service.get_billing_dashboard(organization_id=organization_id)

    return ApiResponse(
        data={
            "mrr_estimate": _to_decimal_string(data.get("mrr_estimate")),
            "open_invoices_count": data.get("open_invoices_count", 0),
            "past_due_invoices_count": data.get("past_due_invoices_count", 0),
            "payments_collected_this_month": _to_decimal_string(
                data.get("payments_collected_this_month")
            ),
            "active_subscriptions_count": data.get("active_subscriptions_count", 0),
        },
        meta={},
        error=None,
    )