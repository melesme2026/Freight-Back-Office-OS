from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from app.api.v1 import billing_invoices, documents, loads, payments
from app.core.exceptions import ForbiddenError, UnauthorizedError


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


def test_driver_cannot_generate_staff_invoice_pdf(db_session) -> None:
    with pytest.raises(ForbiddenError):
        loads.download_load_invoice(
            load_id=uuid.uuid4(),
            token_payload=_driver_token(organization_id=uuid.uuid4(), driver_id=uuid.uuid4()),
            db=db_session,
        )


def test_driver_cannot_export_staff_loads_csv(db_session) -> None:
    with pytest.raises(ForbiddenError):
        loads.export_loads_csv(
            token_payload=_driver_token(organization_id=uuid.uuid4(), driver_id=uuid.uuid4()),
            db=db_session,
        )

def test_driver_mobile_check_in_requires_assigned_load(monkeypatch, db_session) -> None:
    from app.api.v1 import loads

    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    class FakeLoadService:
        def __init__(self, _db) -> None:
            pass

        def get_load(self, _load_id):
            return SimpleNamespace(
                id=uuid.uuid4(),
                organization_id=organization_id,
                driver_id=uuid.uuid4(),
            )

    monkeypatch.setattr(loads, "LoadService", FakeLoadService)

    with pytest.raises(UnauthorizedError):
        loads.driver_load_check_in(
            load_id=uuid.uuid4(),
            payload=loads.DriverLoadCheckInRequest(status="in_transit"),
            token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
            db=db_session,
        )


def test_driver_mobile_check_in_transitions_own_load(monkeypatch, db_session) -> None:
    from app.api.v1 import loads

    organization_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    load_id = uuid.uuid4()
    calls: dict[str, object] = {}

    load = SimpleNamespace(id=load_id, organization_id=organization_id, driver_id=driver_id)

    class FakeLoadService:
        def __init__(self, _db) -> None:
            pass

        def get_load(self, _load_id):
            return load

    class FakeWorkflowEngine:
        def __init__(self, _db) -> None:
            pass

        def transition_load(self, **kwargs):
            calls.update(kwargs)
            return {"old_status": "booked", "new_status": kwargs["new_status"].value}

    monkeypatch.setattr(loads, "LoadService", FakeLoadService)
    monkeypatch.setattr(loads, "WorkflowEngine", FakeWorkflowEngine)
    monkeypatch.setattr(loads, "_serialize_load", lambda item, **_: {"id": str(item.id)})
    monkeypatch.setattr(loads, "_log_load_activity", lambda **_: None)

    response = loads.driver_load_check_in(
        load_id=load_id,
        payload=loads.DriverLoadCheckInRequest(
            status="delivered",
            eta_note="Arrived at consignee",
            latitude=33.749,
            longitude=-84.388,
            location_accuracy_meters=25.2,
        ),
        token_payload=_driver_token(organization_id=organization_id, driver_id=driver_id),
        db=db_session,
    )

    assert response.meta["driver_check_in"] is True
    assert calls["load_id"] == str(load_id)
    assert calls["actor_type"] == "driver"
    assert calls["new_status"] == loads.LoadStatus.DELIVERED
    assert "eta=Arrived at consignee" in str(calls["notes"])
