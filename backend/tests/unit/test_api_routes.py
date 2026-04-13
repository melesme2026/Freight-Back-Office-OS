from __future__ import annotations

from app.main import create_app


def test_core_feature_routes_are_registered() -> None:
    app = create_app()
    routes = {
        (method, route.path)
        for route in app.routes
        for method in (route.methods or set())
    }

    expected_routes = {
        ("PATCH", "/api/v1/organizations/{organization_id}"),
        ("POST", "/api/v1/onboarding/{customer_account_id}/initialize"),
        ("GET", "/api/v1/onboarding/{customer_account_id}"),
        ("PUT", "/api/v1/onboarding/{customer_account_id}"),
        ("GET", "/api/v1/billing-invoices"),
        ("GET", "/api/v1/payments"),
        ("POST", "/api/v1/support/tickets"),
        ("GET", "/api/v1/support/tickets"),
        ("GET", "/api/v1/loads"),
        ("POST", "/api/v1/documents/upload"),
    }

    for method, path in expected_routes:
        assert (method, path) in routes
