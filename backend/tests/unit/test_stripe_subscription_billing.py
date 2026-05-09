from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from app.api.v1.billing import CheckoutSessionRequest, create_checkout_session
from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.enums.role import Role
from app.domain.models.organization import Organization
from app.services.billing.stripe_subscription_service import StripeSubscriptionService
from app.services.billing.subscription_enforcement import (
    can_access_feature,
    require_active_subscription,
)
from app.services.billing.subscription_plans import get_subscription_plan, get_subscription_plans


class _FakeStripeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


class _RequestCapture:
    body = b""


def _settings(**overrides) -> Settings:
    values = {
        "stripe_secret_key": "sk_test_safe",
        "stripe_webhook_secret": "whsec_safe",
        "stripe_price_starter_monthly": "price_starter",
        "stripe_price_growth_monthly": "price_growth",
        "stripe_success_url": "https://app.example.test/billing/success",
        "stripe_cancel_url": "https://app.example.test/billing/cancel",
        "default_trial_days": 14,
    }
    values.update(overrides)
    return Settings(**values)


def _org(*, role_status: str = "none") -> Organization:
    return Organization(
        id=uuid.uuid4(),
        name="Billing Org",
        slug=f"billing-org-{uuid.uuid4().hex[:8]}",
        email="owner@example.test",
        is_active=True,
        billing_provider="none",
        billing_status="trial",
        plan_code="none",
        plan_key="none",
        subscription_status=role_status,
    )


def _signature(payload: bytes, secret: str = "whsec_safe") -> str:
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_subscription_plan_validation_uses_configured_price_ids() -> None:
    plans = get_subscription_plans(_settings())

    assert plans["starter"].stripe_price_id == "price_starter"
    assert plans["growth"].monthly_price == 499
    assert plans["fleet"].contact_sales is True
    assert get_subscription_plan(_settings(), "missing") is None


def test_checkout_missing_config_returns_structured_validation_error(db_session) -> None:
    org = _org()
    db_session.add(org)
    db_session.commit()
    service = StripeSubscriptionService(db_session, _settings(stripe_secret_key=None))

    with pytest.raises(AppError) as exc_info:
        service.create_checkout_session(organization=org, plan_key="starter")

    assert exc_info.value.code == "validation_error"
    assert "STRIPE_SECRET_KEY" in exc_info.value.details["missing"]


def test_owner_checkout_allowed_and_creates_session(db_session, monkeypatch) -> None:
    org = _org()
    db_session.add(org)
    db_session.commit()
    captured = _RequestCapture()

    def fake_urlopen(request, timeout):
        captured.body = request.data
        assert timeout == 10
        assert request.headers["Authorization"] == "Bearer sk_test_safe"
        return _FakeStripeResponse(
            {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}
        )

    monkeypatch.setattr("app.services.billing.stripe_subscription_service.urlopen", fake_urlopen)

    response = create_checkout_session(
        CheckoutSessionRequest(plan_key="starter"),
        token_payload={"organization_id": str(org.id), "role": Role.OWNER.value},
        db=db_session,
        settings=_settings(),
    )

    assert response.data["checkout_url"] == "https://checkout.stripe.test/session"
    assert b"line_items%5B0%5D%5Bprice%5D=price_starter" in captured.body
    assert b"subscription_data%5Btrial_period_days%5D=14" in captured.body


def test_driver_checkout_blocked(db_session) -> None:
    org = _org()
    db_session.add(org)
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        create_checkout_session(
            CheckoutSessionRequest(plan_key="starter"),
            token_payload={"organization_id": str(org.id), "role": Role.DRIVER.value},
            db=db_session,
            settings=_settings(),
        )

    assert exc_info.value.code == "unauthorized"


def test_webhook_signature_validation_rejects_invalid_signature(db_session) -> None:
    service = StripeSubscriptionService(db_session, _settings())

    with pytest.raises(AppError) as exc_info:
        service.verify_webhook_event(payload=b'{"id":"evt_bad"}', signature_header="t=1,v1=bad")

    assert exc_info.value.code == "unauthorized"


def test_checkout_session_completed_updates_organization(db_session) -> None:
    org = _org()
    db_session.add(org)
    db_session.commit()
    event = {
        "id": "evt_checkout_completed",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_123",
                "subscription": "sub_123",
                "client_reference_id": str(org.id),
                "metadata": {"organization_id": str(org.id), "plan_key": "starter"},
            }
        },
    }

    result = StripeSubscriptionService(db_session, _settings()).process_webhook_event(event)

    db_session.refresh(org)
    assert result["processed"] is True
    assert org.billing_provider == "stripe"
    assert org.plan_key == "starter"
    assert org.stripe_customer_id == "cus_123"
    assert org.stripe_subscription_id == "sub_123"


def test_subscription_updated_and_deleted_handling_is_idempotent(db_session) -> None:
    org = _org()
    db_session.add(org)
    db_session.commit()
    now = int(datetime.now(timezone.utc).timestamp())
    event = {
        "id": "evt_sub_updated",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_456",
                "customer": "cus_456",
                "status": "active",
                "metadata": {"organization_id": str(org.id), "plan_key": "growth"},
                "trial_start": now,
                "trial_end": now + 86400,
                "current_period_start": now,
                "current_period_end": now + 2592000,
                "cancel_at_period_end": True,
            }
        },
    }
    service = StripeSubscriptionService(db_session, _settings())

    first = service.process_webhook_event(event)
    duplicate = service.process_webhook_event(event)
    db_session.refresh(org)

    assert first["processed"] is True
    assert duplicate["duplicate"] is True
    assert org.subscription_status == "active"
    assert org.plan_key == "growth"
    assert org.cancel_at_period_end is True

    deleted = dict(event)
    deleted["id"] = "evt_sub_deleted"
    deleted["type"] = "customer.subscription.deleted"
    deleted["data"] = {"object": {**event["data"]["object"], "status": "canceled"}}

    service.process_webhook_event(deleted)
    db_session.refresh(org)
    assert org.subscription_status == "canceled"


def test_verified_webhook_payload_processes_payment_failed(db_session) -> None:
    org = _org(role_status="active")
    org.stripe_customer_id = "cus_failed"
    db_session.add(org)
    db_session.commit()
    payload = json.dumps(
        {
            "id": "evt_invoice_failed",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_failed", "subscription": "sub_failed"}},
        }
    ).encode()
    service = StripeSubscriptionService(db_session, _settings())

    event = service.verify_webhook_event(payload=payload, signature_header=_signature(payload))
    result = service.process_webhook_event(event)
    db_session.refresh(org)

    assert result["processed"] is True
    assert org.subscription_status == "past_due"
    assert org.last_payment_status == "failed"


def test_billing_status_serialization_includes_trial_and_features(db_session) -> None:
    org = _org(role_status="trialing")
    org.plan_key = "starter"
    org.trial_start = datetime.now(timezone.utc)
    org.trial_end = datetime.now(timezone.utc) + timedelta(days=14)
    org.current_period_end = org.trial_end
    db_session.add(org)
    db_session.commit()

    status = StripeSubscriptionService(db_session, _settings()).serialize_status(org)

    assert status["plan"]["key"] == "starter"
    assert status["subscription_status"] == "trialing"
    assert status["trial"]["is_trialing"] is True
    assert status["enforcement_enabled"] is False
    assert status["allowed_features"]["billing"] is True


def test_enforcement_helper_default_safe_behavior() -> None:
    org = _org(role_status="past_due")

    assert (
        can_access_feature(org, "loads", settings=_settings(billing_enforcement_enabled=False))
        is True
    )
    require_active_subscription(org, settings=_settings(billing_enforcement_enabled=False))

    assert (
        can_access_feature(org, "billing", settings=_settings(billing_enforcement_enabled=True))
        is True
    )
    with pytest.raises(AppError) as exc_info:
        require_active_subscription(org, settings=_settings(billing_enforcement_enabled=True))
    assert exc_info.value.code == "billing_error"
