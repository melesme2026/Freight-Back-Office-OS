from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from app.core.dependencies import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse
from app.services.accounting.accounting_export_service import (
    KIND_COLUMNS,
    AccountingExportService,
)
from app.services.audit.audit_service import AuditService
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)

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
    db: Session = GET_DB_SESSION_DEPENDENCY,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
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
    db: Session = GET_DB_SESSION_DEPENDENCY,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
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
    AuditService(db).log_event(
        organization_id=org_id,
        entity_type="accounting_settings",
        entity_id=org_id,
        action="accounting.settings.updated",
        actor_id=str(token_payload.get("sub")) if token_payload.get("sub") else None,
        actor_type="staff_user",
        metadata_json={
            "quickbooks_changed": payload.quickbooks is not None,
            "mapping_changed": payload.mapping is not None,
        },
    )
    db.commit()
    return ApiResponse(data=service.settings_payload(org_id), meta={}, error=None)


@router.get("/exports/{kind}/preview", response_model=ApiResponse)
def preview_accounting_export(
    kind: AccountingKindParam,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
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
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    reconciliation_status: Annotated[str | None, Query()] = None,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
) -> Response:
    _authorize_accounting_read(token_payload)
    org_id = _org_id(token_payload)
    result = _service(db).build_csv_export(
        org_id,
        kind,
        date_from=date_from,
        date_to=date_to,
        status=status,
        reconciliation_status=reconciliation_status,
    )
    AuditService(db).log_event(
        organization_id=org_id,
        entity_type="accounting_export",
        entity_id=org_id,
        action="accounting.export.generated",
        actor_id=str(token_payload.get("sub")) if token_payload.get("sub") else None,
        actor_type="staff_user",
        metadata_json={"export_kind": kind, "row_count": result.row_count},
    )
    db.commit()
    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Export-Row-Count": str(result.row_count),
        "X-Export-Columns": ",".join(result.columns),
    }
    return Response(content=result.content, media_type="text/csv; charset=utf-8", headers=headers)
