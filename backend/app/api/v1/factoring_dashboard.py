from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.load_payment_reconciliation import _authorize_payment_read, _org_id, _serialize
from app.core.dependencies import get_db_session
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.payments.payment_reconciliation_service import PaymentReconciliationService

router = APIRouter(prefix="/factoring-dashboard")


@router.get("", response_model=ApiResponse)
def get_factoring_dashboard(
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_payment_read(token_payload)
    service = PaymentReconciliationService(db)
    records = service.list_factoring_dashboard(_org_id(token_payload))
    return ApiResponse(data=[_serialize(record) for record in records], meta={"total": len(records)}, error=None)
