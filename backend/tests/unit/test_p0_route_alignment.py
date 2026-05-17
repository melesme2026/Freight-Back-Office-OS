from __future__ import annotations

from app.main import create_app

REQUIRED_ROUTES = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/driver-login"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/loads/{load_id}"),
    ("GET", "/api/v1/driver/loads"),
    ("GET", "/api/v1/driver/loads/{load_id}"),
    ("GET", "/api/v1/loads/{load_id}/documents"),
    ("GET", "/api/v1/documents/{document_id}/download"),
    ("GET", "/api/v1/loads/{load_id}/invoice"),
    ("GET", "/api/v1/loads/{load_id}/submission-packets"),
    ("GET", "/api/v1/loads/{load_id}/submission-packets/{packet_id}/download"),
    ("GET", "/api/v1/review-queue"),
}


def test_p0_frontend_backend_route_alignment() -> None:
    app = create_app()
    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    missing = REQUIRED_ROUTES - registered
    assert not missing
