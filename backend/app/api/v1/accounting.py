from __future__ import annotations

# ruff: noqa: B008
from datetime import date
from typing import Any, Literal

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.accounting.accounting_export_service import (
    KIND_COLUMNS,
    AccountingExportService,
)
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

router = APIRouter(prefix="/accounting")

AccountingKindParam = Literal["invoices", "factoring", "settlements", "payments", "aging"]


class AccountingMappingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounting_category: str | None = None
    revenue_category: str | None = None
    factoring_category: str | None = None
    settlement_category: str | None = None
    payment_category: str | None = None


class QuickBooksSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    realm_id: str | None = None
    last_export_note: str | None = None


class AccountingSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping: AccountingMappingPatch | None = None
    quickbooks: QuickBooksSettingsPatch | None = None


def _authorize_accounting_read(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    allowed_roles = {
        "owner",
        "admin",
        "ops",
        "ops_manager",
        "ops_agent",
        "billing",
        "billing_admin",
        "support",
        "support_agent",
        "viewer",
        "staff",
    }
    if role in allowed_roles:
        return
    raise ForbiddenError("Drivers cannot access accounting exports")


def _authorize_accounting_write(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role in {"owner", "admin", "billing", "billing_admin"}:
        return
    raise ForbiddenError("You do not have permission to modify accounting integration settings")


def _org_id(token_payload: dict[str, Any]) -> str:
    org_id = token_payload.get("organization_id")
    if not org_id:
        raise UnauthorizedError("Missing organization context")
    return str(org_id)


def _service(db: Session) -> AccountingExportService:
    return AccountingExportService(db)


@router.get("/settings", response_model=ApiResponse)
def get_accounting_settings(
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_accounting_read(token_payload)
    return ApiResponse(
        data=_service(db).settings_payload(_org_id(token_payload)),
        meta={},
        error=None,
    )


@router.patch("/settings", response_model=ApiResponse)
def update_accounting_settings(
    payload: AccountingSettingsPatch,
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_accounting_write(token_payload)
    service = _service(db)
    org_id = _org_id(token_payload)
    if payload.mapping is not None:
        service.update_mapping(org_id, payload.mapping.model_dump(exclude_unset=True))
    if payload.quickbooks is not None:
        service.update_integration_settings(
            org_id,
            payload.quickbooks.model_dump(exclude_unset=True),
        )
    db.commit()
    return ApiResponse(data=service.settings_payload(org_id), meta={}, error=None)


@router.get("/exports/{kind}/preview", response_model=ApiResponse)
def preview_accounting_export(
    kind: AccountingKindParam,
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> ApiResponse:
    _authorize_accounting_read(token_payload)
    service = _service(db)
    rows = service.preview_rows(_org_id(token_payload), kind)
    return ApiResponse(
        data={"columns": KIND_COLUMNS[kind], "rows": rows},
        meta={"total": len(rows)},
        error=None,
    )


@router.get("/exports/{kind}.csv")
def export_accounting_csv(
    kind: AccountingKindParam,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    reconciliation_status: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
) -> Response:
    _authorize_accounting_read(token_payload)
    result = _service(db).build_csv_export(
        _org_id(token_payload),
        kind,
        date_from=date_from,
        date_to=date_to,
        status=status,
        reconciliation_status=reconciliation_status,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Export-Row-Count": str(result.row_count),
        "X-Export-Columns": ",".join(result.columns),
    }
    return Response(content=result.content, media_type="text/csv; charset=utf-8", headers=headers)
