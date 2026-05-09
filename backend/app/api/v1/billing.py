from __future__ import annotations

import uuid
from typing import Any

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.domain.models.organization import Organization
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.common import ApiResponse
from app.services.audit.audit_service import AuditService
from app.services.billing.stripe_subscription_service import StripeSubscriptionService
from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)
GET_SETTINGS_DEPENDENCY = Depends(get_settings)

router = APIRouter(prefix="/billing")

OWNER_ADMIN_ROLES = {"owner", "admin", "billing_admin"}


class CheckoutSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_key: str


def _token_org_id(token_payload: dict[str, Any]) -> uuid.UUID:
    raw_org_id = str(token_payload.get("organization_id") or "").strip()
    if not raw_org_id:
        raise UnauthorizedError("Token organization_id is missing")
    try:
        return uuid.UUID(raw_org_id)
    except ValueError as exc:
        raise UnauthorizedError("Token organization_id is invalid") from exc


def _require_owner_admin(token_payload: dict[str, Any]) -> None:
    role = str(token_payload.get("role") or "").strip().lower()
    if role not in OWNER_ADMIN_ROLES:
        raise UnauthorizedError("Owner or admin role required")


def _get_token_organization(db: Session, token_payload: dict[str, Any]) -> Organization:
    org_id = _token_org_id(token_payload)
    organization = OrganizationRepository(db).get_by_id(org_id)
    if organization is None:
        raise NotFoundError("Organization not found", details={"organization_id": str(org_id)})
    return organization


@router.get("/status", response_model=ApiResponse)
def get_billing_status(
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    settings: Settings = GET_SETTINGS_DEPENDENCY,
) -> ApiResponse:
    organization = _get_token_organization(db, token_payload)
    service = StripeSubscriptionService(db, settings)
    return ApiResponse(data=service.serialize_status(organization), meta={}, error=None)


@router.post("/checkout-session", response_model=ApiResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    settings: Settings = GET_SETTINGS_DEPENDENCY,
) -> ApiResponse:
    _require_owner_admin(token_payload)
    organization = _get_token_organization(db, token_payload)
    service = StripeSubscriptionService(db, settings)
    result = service.create_checkout_session(organization=organization, plan_key=payload.plan_key)
    AuditService(db).log_event(
        organization_id=str(organization.id),
        entity_type="billing_subscription",
        entity_id=str(organization.id),
        action="billing.checkout_session.created",
        actor_id=str(token_payload.get("sub")) if token_payload.get("sub") else None,
        actor_type="staff_user",
        metadata_json={"status": "checkout_started"},
    )
    db.commit()
    return ApiResponse(data=result, meta={}, error=None)


@router.post("/stripe/webhook", response_model=ApiResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = GET_DB_SESSION_DEPENDENCY,
    settings: Settings = GET_SETTINGS_DEPENDENCY,
) -> ApiResponse:
    payload = await request.body()
    service = StripeSubscriptionService(db, settings)
    event = service.verify_webhook_event(payload=payload, signature_header=stripe_signature)
    result = service.process_webhook_event(event)
    return ApiResponse(data=result, meta={}, error=None)
