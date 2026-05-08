from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.domain.enums.factoring import FactoringWorkflowStatus
from app.schemas.common import ApiResponse
from app.services.reports.money_dashboard_service import MoneyDashboardService
from app.services.reports.operational_analytics_service import OperationalAnalyticsService


router = APIRouter()


def _authorize_reports_read(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role == "driver":
        raise ForbiddenError("Drivers cannot access operational reports")


@router.get("/reports/money-dashboard", response_model=ApiResponse)
def get_money_dashboard(
    *,
    organization_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    token_payload: dict[str, object] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _authorize_reports_read(token_payload)

    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    service = MoneyDashboardService(db)
    data = service.get_money_dashboard(
        org_id=str(effective_org_id),
        date_from=date_from,
        date_to=date_to,
    )

    return ApiResponse(data=data, meta={}, error=None)


@router.get("/reports/operational-analytics", response_model=ApiResponse)
def get_operational_analytics(
    *,
    organization_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    broker_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    factoring_status: FactoringWorkflowStatus | None = None,
    token_payload: dict[str, object] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _authorize_reports_read(token_payload)

    token_org_id = token_payload.get("organization_id")
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    service = OperationalAnalyticsService(db)
    data = service.get_operational_analytics(
        org_id=str(effective_org_id),
        date_from=date_from,
        date_to=date_to,
        broker_id=str(broker_id) if broker_id else None,
        driver_id=str(driver_id) if driver_id else None,
        factoring_status=factoring_status.value if factoring_status else None,
    )

    return ApiResponse(data=data, meta={}, error=None)
