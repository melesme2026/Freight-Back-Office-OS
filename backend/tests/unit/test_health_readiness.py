from app.api.v1.health import _build_readiness_payload


def test_readiness_payload_shape():
    payload, _ = _build_readiness_payload()
    assert payload["status"] in {"ok", "degraded"}
    assert "checks" in payload
    for key in ["app", "database", "storage", "redis", "migrations", "email"]:
        assert key in payload["checks"]
