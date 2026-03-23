from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.billing.billing_service import BillingService


router = APIRouter()


@router.get("/billing/dashboard", response_model=ApiResponse)
def get_billing_dashboard(
    *,
    organization_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    if organization_id:
        try:
            uuid.UUID(organization_id)
        except ValueError as exc:
            raise ValidationError(
                "Invalid organization_id",
                details={"organization_id": organization_id},
            ) from exc

    service = BillingService(db)
    data = service.get_billing_dashboard(organization_id=organization_id)

    return ApiResponse(
        data={
            "mrr_estimate": format(data["mrr_estimate"], "f"),
            "open_invoices_count": data["open_invoices_count"],
            "past_due_invoices_count": data["past_due_invoices_count"],
            "payments_collected_this_month": format(
                data["payments_collected_this_month"], "f"
            ),
            "active_subscriptions_count": data["active_subscriptions_count"],
        },
        meta={},
        error=None,
    )