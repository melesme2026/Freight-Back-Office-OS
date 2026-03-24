Paste this into:

docs/api/webhook-contracts.md

# Webhook Contracts

## Purpose

This document defines the structure and expectations for webhook-based ingestion endpoints.

It ensures:

- consistent payload handling
- predictable ingestion behavior
- safe processing of external events

---

## Supported webhook channels

The system currently supports:

- WhatsApp (driver messages / documents)
- Email (future)
- Payment providers (Stripe, etc.)

---

## General webhook contract

All webhook endpoints follow:

- POST request
- JSON payload
- idempotent processing
- fast acknowledgment (no long processing inline)

---

## Standard response

All webhook endpoints should return:

```json
{
  "accepted": true,
  "channel": "<channel>",
  "received_at": "<timestamp>"
}


⸻

Idempotency

Webhooks must be safe to retry.

Guidelines:
	•	use unique event ID if provided
	•	avoid duplicate processing
	•	log processed events

⸻

1. WhatsApp webhook

Endpoint

POST /api/v1/webhooks/whatsapp


⸻

Sample payload (simplified)

{
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
                "text": {
                  "body": "Load document attached"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}


⸻

Expected behavior
	•	accept payload
	•	extract sender (driver)
	•	extract message content
	•	route to ingestion service
	•	store raw payload

⸻

2. Email webhook (future)

Endpoint

POST /api/v1/webhooks/email


⸻

Expected payload (example)

{
  "from": "driver@example.com",
  "subject": "Invoice attached",
  "attachments": [
    {
      "filename": "invoice.pdf",
      "url": "https://..."
    }
  ]
}


⸻

Expected behavior
	•	extract sender
	•	download attachments
	•	create document records
	•	trigger processing pipeline

⸻

3. Payment webhook

Endpoint

POST /api/v1/webhooks/payment


⸻

Sample payload (Stripe-like)

{
  "provider": "stripe",
  "event": {
    "id": "evt_123",
    "type": "payment_intent.succeeded",
    "data": {
      "object": {
        "id": "pi_123",
        "amount": 12500,
        "currency": "usd",
        "status": "succeeded"
      }
    }
  }
}


⸻

Expected behavior
	•	verify provider (future: signature validation)
	•	map payment to invoice
	•	update payment status
	•	update invoice balance
	•	record event

⸻

Security considerations

Validation (future)
	•	verify webhook signatures
	•	whitelist source IPs
	•	validate payload schema

⸻

Processing strategy

Webhook endpoints should:
	1.	receive payload
	2.	validate structure
	3.	store raw payload
	4.	enqueue background task
	5.	return response quickly

Avoid:
	•	long synchronous processing
	•	blocking operations

⸻

Error handling

If payload is invalid:

{
  "accepted": false,
  "error": "Invalid payload"
}


⸻

Logging

For each webhook:
	•	store raw payload
	•	log timestamp
	•	log processing result

⸻

Retry handling

External systems may retry:
	•	ensure idempotency
	•	avoid duplicate records
	•	track processed event IDs

⸻

Future improvements
	•	signature verification
	•	retry queue management
	•	webhook replay tools
	•	monitoring dashboard

⸻

Summary

Webhook contracts ensure:
	•	safe ingestion of external events
	•	consistent processing
	•	reliability under retries
	•	foundation for integrations

They are critical for connecting the system to real-world inputs.

---

## Next file (aligned with your structure)

```text
docs/product/roadmap.md