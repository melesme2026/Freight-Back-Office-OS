from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.core.exceptions import BillingError, NotFoundError, UnauthorizedError, ValidationError
from app.domain.models.organization import Organization
from app.domain.models.stripe_webhook_event import StripeWebhookEvent
from app.services.audit.audit_service import AuditService
from app.services.billing.subscription_enforcement import allowed_features
from app.services.billing.subscription_plans import (
    SubscriptionPlan,
    get_subscription_plan,
    get_subscription_plans,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CHECKOUT_ENDPOINT = "https://api.stripe.com/v1/checkout/sessions"
HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
}
STATUS_MAP = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "unpaid": "unpaid",
    "canceled": "canceled",
    "cancelled": "canceled",
    "incomplete": "incomplete",
    "incomplete_expired": "incomplete",
    "none": "none",
}


def utc_from_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class StripeSubscriptionService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def list_plans(self) -> list[SubscriptionPlan]:
        return list(get_subscription_plans(self.settings).values())

    def create_checkout_session(
        self,
        *,
        organization: Organization,
        plan_key: str,
    ) -> dict[str, str]:
        plan = self._validate_checkout_plan(plan_key)
        self._ensure_checkout_config()

        params: dict[str, Any] = {
            "mode": "subscription",
            "success_url": self.settings.stripe_success_url,
            "cancel_url": self.settings.stripe_cancel_url,
            "client_reference_id": str(organization.id),
            "line_items[0][price]": plan.stripe_price_id,
            "line_items[0][quantity]": "1",
            "subscription_data[metadata][organization_id]": str(organization.id),
            "subscription_data[metadata][plan_key]": plan.key,
            "metadata[organization_id]": str(organization.id),
            "metadata[plan_key]": plan.key,
        }
        if organization.stripe_customer_id:
            params["customer"] = organization.stripe_customer_id
        elif organization.email:
            params["customer_email"] = organization.email
        if self.settings.default_trial_days > 0:
            params["subscription_data[trial_period_days]"] = str(self.settings.default_trial_days)

        session = self._post_stripe_checkout(params)
        checkout_url = session.get("url")
        session_id = session.get("id")
        if not isinstance(checkout_url, str) or not checkout_url:
            logger.error(
                "Stripe checkout session response omitted checkout URL",
                extra={"organization_id": str(organization.id)},
            )
            raise BillingError("Unable to create checkout session")
        return {"checkout_url": checkout_url, "session_id": str(session_id or "")}

    def serialize_status(self, organization: Organization) -> dict[str, Any]:
        status = self._effective_subscription_status(organization)
        plan_key = organization.plan_key or organization.plan_code or "none"
        plan = get_subscription_plan(self.settings, plan_key)
        return {
            "plan": self._serialize_plan(plan),
            "subscription_status": status,
            "trial": {
                "is_trialing": status == "trialing",
                "trial_start": self._iso(organization.trial_start),
                "trial_end": self._iso(organization.trial_end),
            },
            "enforcement_enabled": self.settings.billing_enforcement_enabled,
            "allowed_features": allowed_features(organization, settings=self.settings),
            "current_period_start": self._iso(organization.current_period_start),
            "current_period_end": self._iso(organization.current_period_end),
            "next_renewal_at": (
                None
                if organization.cancel_at_period_end
                else self._iso(organization.current_period_end)
            ),
            "cancel_at_period_end": organization.cancel_at_period_end,
            "last_payment_status": organization.last_payment_status,
        }

    def verify_webhook_event(
        self,
        *,
        payload: bytes,
        signature_header: str | None,
    ) -> dict[str, Any]:
        if not self.settings.stripe_webhook_secret:
            raise ValidationError(
                "Stripe webhook is not configured",
                details={"config": "STRIPE_WEBHOOK_SECRET"},
            )
        if not signature_header:
            raise UnauthorizedError("Missing Stripe signature")
        timestamp, signatures = self._parse_signature_header(signature_header)
        if abs(time.time() - timestamp) > 300:
            raise UnauthorizedError("Invalid Stripe signature")
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            self.settings.stripe_webhook_secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        if not any(hmac.compare_digest(expected, signature) for signature in signatures):
            raise UnauthorizedError("Invalid Stripe signature")
        try:
            event = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Invalid Stripe webhook payload") from exc
        if not isinstance(event, dict):
            raise ValidationError("Invalid Stripe webhook payload")
        return event

    def process_webhook_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event.get("id") or "").strip()
        event_type = str(event.get("type") or "").strip()
        if not event_id or not event_type:
            raise ValidationError("Invalid Stripe event")

        existing = self.db.scalar(
            select(StripeWebhookEvent).where(
                StripeWebhookEvent.stripe_event_id == event_id,
            ),
        )
        if existing is not None and existing.status == "processed":
            return {
                "event_id": event_id,
                "event_type": event_type,
                "processed": False,
                "duplicate": True,
            }

        record = existing or StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            status="processing",
        )
        self.db.add(record)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return {
                "event_id": event_id,
                "event_type": event_type,
                "processed": False,
                "duplicate": True,
            }

        if event_type not in HANDLED_EVENTS:
            record.status = "ignored"
            record.processed_at = datetime.now(timezone.utc)
            self.db.add(record)
            self.db.commit()
            return {
                "event_id": event_id,
                "event_type": event_type,
                "processed": False,
                "ignored": True,
            }

        obj = (
            ((event.get("data") or {}).get("object") or {})
            if isinstance(event.get("data"), dict)
            else {}
        )
        if not isinstance(obj, dict):
            raise ValidationError("Invalid Stripe event object")
        organization = self._find_organization_for_object(obj)
        if organization is None:
            raise NotFoundError(
                "Organization not found for Stripe event",
                details={"event_type": event_type},
            )

        self._apply_event(event_type, obj, organization)
        record.organization_id = organization.id
        record.status = "processed"
        record.processed_at = datetime.now(timezone.utc)
        record.error_message = None
        self.db.add(record)
        self.db.add(organization)
        AuditService(self.db).log_event(
            organization_id=str(organization.id),
            entity_type="billing_subscription",
            entity_id=str(organization.id),
            action="billing.subscription.changed",
            actor_type="system",
            metadata_json={"status": organization.subscription_status, "event_type": event_type},
        )
        self.db.commit()
        return {
            "event_id": event_id,
            "event_type": event_type,
            "processed": True,
            "duplicate": False,
        }

    def _validate_checkout_plan(self, plan_key: str) -> SubscriptionPlan:
        plan = get_subscription_plan(self.settings, plan_key)
        if plan is None or not plan.active:
            raise ValidationError("Invalid subscription plan", details={"plan_key": plan_key})
        if plan.contact_sales:
            raise ValidationError("Plan requires contact sales", details={"plan_key": plan.key})
        if not plan.stripe_price_id:
            raise ValidationError(
                "Stripe price is not configured for plan",
                details={"plan_key": plan.key},
            )
        return plan

    def _ensure_checkout_config(self) -> None:
        missing = []
        if not self.settings.stripe_secret_key:
            missing.append("STRIPE_SECRET_KEY")
        if not self.settings.stripe_success_url:
            missing.append("STRIPE_SUCCESS_URL")
        if not self.settings.stripe_cancel_url:
            missing.append("STRIPE_CANCEL_URL")
        if missing:
            raise ValidationError("Stripe checkout is not configured", details={"missing": missing})

    def _post_stripe_checkout(self, params: dict[str, Any]) -> dict[str, Any]:
        encoded = urlencode(
            {key: value for key, value in params.items() if value is not None},
        ).encode()
        request = Request(
            CHECKOUT_ENDPOINT,
            data=encoded,
            headers={
                "Authorization": f"Bearer {self.settings.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - Stripe API HTTPS endpoint.
                body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.warning(
                "Stripe checkout session creation failed",
                extra={"error_type": type(exc).__name__},
            )
            raise BillingError("Unable to create checkout session") from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise BillingError("Unable to create checkout session") from exc
        if not isinstance(parsed, dict):
            raise BillingError("Unable to create checkout session")
        return parsed

    def _parse_signature_header(self, signature_header: str) -> tuple[int, list[str]]:
        timestamp: int | None = None
        signatures: list[str] = []
        for item in signature_header.split(","):
            key, _, value = item.partition("=")
            if key == "t":
                try:
                    timestamp = int(value)
                except ValueError as exc:
                    raise UnauthorizedError("Invalid Stripe signature") from exc
            elif key == "v1" and value:
                signatures.append(value)
        if timestamp is None or not signatures:
            raise UnauthorizedError("Invalid Stripe signature")
        return timestamp, signatures

    def _find_organization_for_object(self, obj: dict[str, Any]) -> Organization | None:
        metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        org_id = str(
            metadata.get("organization_id")
            or obj.get("client_reference_id")
            or "",
        ).strip()
        if org_id:
            org = self.db.get(Organization, org_id)
            if org is not None:
                return org
        customer_id = str(obj.get("customer") or "").strip()
        if customer_id:
            org = self.db.scalar(
                select(Organization).where(Organization.stripe_customer_id == customer_id),
            )
            if org is not None:
                return org
        subscription_id = str(obj.get("subscription") or obj.get("id") or "").strip()
        if subscription_id:
            return self.db.scalar(
                select(Organization).where(
                    Organization.stripe_subscription_id == subscription_id,
                ),
            )
        return None

    def _apply_event(
        self,
        event_type: str,
        obj: dict[str, Any],
        organization: Organization,
    ) -> None:
        if event_type == "checkout.session.completed":
            self._apply_checkout_session(obj, organization)
            return
        if event_type.startswith("customer.subscription."):
            self._apply_subscription(obj, organization)
            return
        if event_type == "invoice.payment_succeeded":
            organization.last_payment_status = "succeeded"
            if organization.subscription_status in {"past_due", "unpaid", "incomplete", "none"}:
                organization.subscription_status = "active"
                organization.billing_status = "active"
            return
        if event_type == "invoice.payment_failed":
            organization.last_payment_status = "failed"
            if organization.subscription_status != "canceled":
                organization.subscription_status = "past_due"
                organization.billing_status = "past_due"

    def _apply_checkout_session(self, obj: dict[str, Any], organization: Organization) -> None:
        metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        plan_key = str(
            metadata.get("plan_key")
            or organization.plan_key
            or organization.plan_code
            or "none",
        ).strip().lower()
        subscription_id = str(obj.get("subscription") or "").strip() or None
        customer_id = str(obj.get("customer") or "").strip() or None
        organization.billing_provider = "stripe"
        organization.plan_key = plan_key
        organization.plan_code = plan_key
        if customer_id:
            organization.stripe_customer_id = customer_id
        if subscription_id:
            organization.stripe_subscription_id = subscription_id
        if organization.subscription_status == "none":
            organization.subscription_status = "incomplete"
            organization.billing_status = "inactive"

    def _apply_subscription(self, obj: dict[str, Any], organization: Organization) -> None:
        metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        plan_key = str(
            metadata.get("plan_key")
            or organization.plan_key
            or organization.plan_code
            or "none",
        ).strip().lower()
        stripe_status = str(obj.get("status") or "none").strip().lower()
        status = STATUS_MAP.get(stripe_status, "incomplete")
        if obj.get("customer"):
            organization.stripe_customer_id = str(obj.get("customer"))
        if obj.get("id"):
            organization.stripe_subscription_id = str(obj.get("id"))
        organization.billing_provider = "stripe"
        organization.plan_key = plan_key
        organization.plan_code = plan_key
        organization.subscription_status = (
            "canceled" if obj.get("canceled_at") and status == "active" else status
        )
        organization.billing_status = (
            "canceled"
            if organization.subscription_status == "canceled"
            else organization.subscription_status
        )
        organization.trial_start = utc_from_timestamp(obj.get("trial_start"))
        organization.trial_end = utc_from_timestamp(obj.get("trial_end"))
        organization.current_period_start = utc_from_timestamp(obj.get("current_period_start"))
        organization.current_period_end = utc_from_timestamp(obj.get("current_period_end"))
        organization.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
        if organization.subscription_status == "canceled":
            organization.cancel_at_period_end = False

    def _effective_subscription_status(self, organization: Organization) -> str:
        status = (organization.subscription_status or "none").strip().lower()
        if status != "none":
            return status
        legacy = (organization.billing_status or "").strip().lower()
        if legacy == "trial":
            return "trialing"
        if legacy == "active" or legacy == "manual_active":
            return "active"
        if legacy == "past_due":
            return "past_due"
        if legacy == "canceled":
            return "canceled"
        return "none"

    def _serialize_plan(self, plan: SubscriptionPlan | None) -> dict[str, Any]:
        if plan is None:
            return {
                "key": "none",
                "display_name": "No plan",
                "monthly_price": None,
                "feature_limits": {},
                "active": False,
                "contact_sales": False,
            }
        return {
            "key": plan.key,
            "display_name": plan.display_name,
            "monthly_price": plan.monthly_price,
            "feature_limits": plan.feature_limits,
            "active": plan.active,
            "contact_sales": plan.contact_sales,
        }

    def _iso(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None
