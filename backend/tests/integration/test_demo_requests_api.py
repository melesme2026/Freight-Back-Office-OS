from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.demo_requests import create_demo_request
from app.domain.models.demo_request import DemoRequest
from app.schemas.demo_requests import DemoRequestCreateRequest


def test_demo_request_valid_returns_201_and_saves(db_session):
    payload = DemoRequestCreateRequest(
        full_name="  Jane Doe  ",
        email="  JANE@EXAMPLE.COM ",
        company="  Acme Freight ",
        message="  Need a walkthrough.  ",
    )
    response = create_demo_request(payload=payload, db=db_session)
    assert response.data["status"] == "received"

    row = db_session.query(DemoRequest).one()
    assert row.full_name == "Jane Doe"
    assert row.company == "Acme Freight"
    assert row.email == "jane@example.com"
    assert row.message == "Need a walkthrough."


def test_demo_request_missing_full_name_returns_422():
    with pytest.raises(ValidationError):
        DemoRequestCreateRequest(email="a@b.com", company="Acme")


def test_demo_request_invalid_email_returns_422():
    with pytest.raises(ValidationError):
        DemoRequestCreateRequest(full_name="Jane", email="invalid", company="Acme")


def test_demo_request_missing_company_returns_422():
    with pytest.raises(ValidationError):
        DemoRequestCreateRequest(full_name="Jane", email="jane@example.com")


def test_demo_request_forbids_extra_fields():
    with pytest.raises(ValidationError):
        DemoRequestCreateRequest(full_name="Jane", email="jane@example.com", company="Acme", unexpected="x")
