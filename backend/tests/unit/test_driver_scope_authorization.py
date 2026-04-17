from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.api.v1 import billing_invoices, documents, payments
from app.core.exceptions import UnauthorizedError


def _driver_token(*, organization_id: uuid.UUID, driver_id: uuid.UUID) -> dict[str, str]:
    return {
        "organization_id": str(organization_id),
        "role": "driver",
        "driver_id": str(driver_id),
        "sub": str(uuid.uuid4()),
    }


def test_driver_document_list_is_force_scoped(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    seen: dict[str, str | None] = {"driver_id": None}

    class FakeDocumentService:
        def __init__(self, _db) -> None:
            pass

        def list_documents(self, **kwargs):
            seen["driver_id"] = kwargs.get("driver_id")
            return ([], 0)

    monkeypatch.setattr(documents, "DocumentService", FakeDocumentService)

    response = documents.list_documents(
        token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
        db=db_session,
    )

    assert response.meta["total_count"] == 0
    assert seen["driver_id"] == str(driver_id)


def test_driver_document_list_rejects_other_driver_filter(db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    with pytest.raises(UnauthorizedError):
        documents.list_documents(
            token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
            driver_id=uuid.uuid4(),
            db=db_session,
        )


def test_driver_cannot_read_other_driver_document(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    class FakeDocumentService:
        def __init__(self, _db) -> None:
            pass

        def get_document(self, _document_id):
            return SimpleNamespace(
                id=uuid.uuid4(),
                organization_id=organization_id,
                driver_id=uuid.uuid4(),
                storage_key="uploads/sample.pdf",
            )

    monkeypatch.setattr(documents, "DocumentService", FakeDocumentService)

    with pytest.raises(UnauthorizedError):
        documents.get_document(
            document_id=uuid.uuid4(),
            token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
            db=db_session,
        )


def test_driver_payment_list_is_force_scoped(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    seen: dict[str, str | None] = {"driver_id": None}

    class FakePaymentService:
        def __init__(self, _db) -> None:
            pass

        def list_payments(self, **kwargs):
            seen["driver_id"] = kwargs.get("driver_id")
            return ([], 0)

    monkeypatch.setattr(payments, "PaymentService", FakePaymentService)

    response = payments.list_payments(
        token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
        db=db_session,
    )

    assert response.meta["total"] == 0
    assert seen["driver_id"] == str(driver_id)


def test_driver_payment_read_requires_driver_ownership(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    class FakePaymentService:
        def __init__(self, _db) -> None:
            pass

        def get_payment(self, _payment_id):
            return SimpleNamespace(
                id=uuid.uuid4(),
                organization_id=organization_id,
                driver_id=uuid.uuid4(),
            )

    monkeypatch.setattr(payments, "PaymentService", FakePaymentService)

    with pytest.raises(UnauthorizedError):
        payments.get_payment(
            payment_id=uuid.uuid4(),
            token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
            db=db_session,
        )


def test_driver_invoice_list_is_force_scoped(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    seen: dict[str, str | None] = {"driver_id": None}

    class FakeInvoiceService:
        def __init__(self, _db) -> None:
            pass

        def list_invoices(self, **kwargs):
            seen["driver_id"] = kwargs.get("driver_id")
            return ([], 0)

    monkeypatch.setattr(billing_invoices, "InvoiceService", FakeInvoiceService)

    response = billing_invoices.list_billing_invoices(
        token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
        db=db_session,
    )

    assert response.meta["total"] == 0
    assert seen["driver_id"] == str(driver_id)


def test_driver_invoice_read_requires_driver_payment_association(monkeypatch, db_session) -> None:
    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    class FakeInvoiceService:
        def __init__(self, _db) -> None:
            pass

        def get_invoice(self, _invoice_id):
            return SimpleNamespace(
                id=uuid.uuid4(),
                organization_id=organization_id,
                payments=[SimpleNamespace(driver_id=uuid.uuid4())],
                lines=[],
            )

    monkeypatch.setattr(billing_invoices, "InvoiceService", FakeInvoiceService)

    with pytest.raises(UnauthorizedError):
        billing_invoices.get_billing_invoice(
            invoice_id=uuid.uuid4(),
            token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
            db=db_session,
        )


def test_driver_billing_mutation_endpoints_are_blocked(db_session) -> None:
    token_payload = _driver_token(organization_id=uuid.uuid4(), driver_id=uuid.uuid4())

    with pytest.raises(UnauthorizedError):
        payments._ensure_staff_role_for_mutation(token_payload)

    with pytest.raises(UnauthorizedError):
        billing_invoices._ensure_staff_role_for_mutation(token_payload)

    with pytest.raises(UnauthorizedError):
        documents._ensure_staff_role(token_payload)
