# Webhook Contracts

## Purpose

This document defines the structure and expectations for webhook-based ingestion endpoints.

It ensures:

* consistent payload handling
* predictable ingestion behavior
* safe processing of external events

---

## Supported webhook channels

The system currently supports:

* WhatsApp (driver messages and documents)
* email (future)
* payment providers (Stripe, etc.)

---

## General webhook contract

All webhook endpoints should follow these principles:

* `POST` request
* JSON payload unless the provider requires otherwise
* idempotent processing
* fast acknowledgment with no long-running inline work

---

## Standard response

All webhook endpoints should return a lightweight acknowledgment:

```json
{
  "accepted": true,
  "channel": "<channel>",
  "received_at": "<timestamp>"
}
```

---

## Idempotency

Webhooks must be safe to retry.

Guidelines:

* use a unique event ID if the provider supplies one
* avoid duplicate processing
* log or persist processed event identifiers

---

## 1. WhatsApp webhook

### Endpoint

```text
POST /api/v1/webhooks/whatsapp
```

### Sample payload (simplified)

```json
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
```

### Expected behavior

* accept the payload
* extract the sender or driver identifier
* extract message content and attachments if present
* route the event to the ingestion service
* store the raw payload for traceability

---

## 2. Email webhook (future)

### Endpoint

```text
POST /api/v1/webhooks/email
```

### Expected payload (example)

```json
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
```

### Expected behavior

* extract sender information
* download or fetch attachments through the approved ingestion flow
* create document records
* trigger the processing pipeline

---

## 3. Payment webhook

### Endpoint

```text
POST /api/v1/webhooks/payment
```

### Sample payload (Stripe-like)

```json
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
```

### Expected behavior

* verify the provider context
* support future signature validation
* map the payment to the correct invoice or account
* update payment status
* update invoice balance if applicable
* record the inbound event

---

## Security considerations

### Validation (future)

* verify webhook signatures
* allowlist source IPs where supported and appropriate
* validate payload schemas before processing

---

## Processing strategy

Webhook endpoints should:

1. receive the payload
2. validate the structure
3. store the raw payload
4. enqueue a background task
5. return a response quickly

Avoid:

* long synchronous processing
* blocking operations in the request path

---

## Error handling

If the payload is invalid, return a structured failure response.

```json
{
  "accepted": false,
  "error": "Invalid payload"
}
```

---

## Logging

For each webhook event:

* store the raw payload
* log the timestamp
* log the processing result

---

## Retry handling

External systems may retry delivery. The system should:

* ensure idempotency
* avoid duplicate records
* track processed event IDs where available

---

## Future improvements

* signature verification
* retry queue management
* webhook replay tools
* monitoring dashboard

---

## Summary

Webhook contracts help ensure:

* safe ingestion of external events
* consistent processing
* reliability under retries
* a stable foundation for integrations

They are critical for connecting the system to real-world inputs.
