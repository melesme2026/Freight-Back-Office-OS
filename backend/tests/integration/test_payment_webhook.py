from __future__ import annotations

from app.services.ingestion.api_ingestion_service import ApiIngestionService


def test_payment_webhook_ingestion_accepts_payload() -> None:
    service = ApiIngestionService()

    payload = {
        "provider": "stripe",
        "event": {
            "id": "evt_test_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "amount": 12500,
                    "currency": "usd",
                    "status": "succeeded",
                }
            },
        },
    }

    result = service.ingest(payload)

    assert result["accepted"] is True
    assert result["channel"] == "api"
    assert result["payload"] == payload
    assert "received_at" in result