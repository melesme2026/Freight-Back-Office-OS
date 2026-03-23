from __future__ import annotations

from app.services.ingestion.whatsapp_ingestion_service import WhatsAppIngestionService


def test_whatsapp_ingestion_accepts_payload() -> None:
    service = WhatsAppIngestionService()

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid-123",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": "Load document attached"},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }

    result = service.ingest(payload)

    assert result["accepted"] is True
    assert result["channel"] == "whatsapp"
    assert result["payload"] == payload
    assert "received_at" in result