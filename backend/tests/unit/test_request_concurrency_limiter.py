from __future__ import annotations

from types import SimpleNamespace

from app.core.middleware import RequestConcurrencyLimitMiddleware


class _Url:
    def __init__(self, path: str) -> None:
        self.path = path


def _request(method: str, path: str):
    return SimpleNamespace(method=method, url=_Url(path))


def test_concurrency_limiter_separates_background_reads_from_document_writes() -> None:
    middleware = RequestConcurrencyLimitMiddleware(app=None)  # type: ignore[arg-type]

    assert (
        middleware._bucket_for_request(
            _request("GET", "/api/v1/loads/00000000-0000-0000-0000-000000000001/documents")
        )
        == "background_panel_reads"
    )
    assert (
        middleware._bucket_for_request(
            _request("GET", "/api/v1/loads/00000000-0000-0000-0000-000000000001/invoice-status")
        )
        == "background_panel_reads"
    )
    assert (
        middleware._bucket_for_request(_request("POST", "/api/v1/documents/upload"))
        == "document_writes"
    )
    assert (
        middleware._bucket_for_request(
            _request("GET", "/api/v1/documents/00000000-0000-0000-0000-000000000002/download")
        )
        == "document_writes"
    )
    assert (
        middleware._bucket_for_request(
            _request("DELETE", "/api/v1/documents/00000000-0000-0000-0000-000000000002")
        )
        == "document_writes"
    )


def test_concurrency_limiter_separates_invoice_and_workflow_actions() -> None:
    middleware = RequestConcurrencyLimitMiddleware(app=None)  # type: ignore[arg-type]

    assert (
        middleware._bucket_for_request(
            _request("GET", "/api/v1/loads/00000000-0000-0000-0000-000000000001/invoice")
        )
        == "invoice_actions"
    )
    assert (
        middleware._bucket_for_request(
            _request("POST", "/api/v1/loads/00000000-0000-0000-0000-000000000001/workflow-actions")
        )
        == "workflow_status_mutations"
    )


def test_concurrency_limiter_bypasses_auth_and_health() -> None:
    middleware = RequestConcurrencyLimitMiddleware(app=None)  # type: ignore[arg-type]

    assert middleware._bucket_for_request(_request("POST", "/api/v1/auth/login")) is None
    assert middleware._bucket_for_request(_request("GET", "/api/v1/health")) is None
