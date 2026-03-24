Paste this into:

docs/api/endpoint-contracts.md

# Endpoint Contracts

## Purpose

This document defines the expected request and response contracts for core API endpoints.

It ensures:

- consistency across services
- clear frontend-backend integration
- predictable behavior for consumers

---

## Standard response format

All endpoints should follow:

```json
{
  "data": {},
  "meta": {},
  "error": null
}


⸻

Success response

{
  "data": {
    "id": "123",
    "status": "validated"
  }
}


⸻

Error response

{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Missing required fields"
  }
}


⸻

Authentication (future)

Headers:

Authorization: Bearer <token>


⸻

Core endpoint groups

⸻

1. Health

GET /api/v1/health

Response:

{
  "data": {
    "status": "ok"
  }
}


⸻

2. Loads

POST /api/v1/loads

Request:

{
  "load_number": "LOAD-1001",
  "gross_amount": "1200.00"
}

Response:

{
  "data": {
    "id": "uuid",
    "status": "new"
  }
}


⸻

GET /api/v1/loads/{id}

Response:

{
  "data": {
    "id": "uuid",
    "status": "validated",
    "gross_amount": "1200.00"
  }
}


⸻

PATCH /api/v1/loads/{id}

Request:

{
  "status": "validated"
}


⸻

3. Documents

POST /api/v1/documents

Request (multipart):
	•	file
	•	metadata (optional)

Response:

{
  "data": {
    "id": "uuid",
    "status": "pending"
  }
}


⸻

GET /api/v1/documents/{id}

Response:

{
  "data": {
    "id": "uuid",
    "document_type": "invoice",
    "processing_status": "completed"
  }
}


⸻

4. Review Queue

GET /api/v1/review-queue

Response:

{
  "data": [
    {
      "load_id": "uuid",
      "issues": ["missing_signature"]
    }
  ],
  "meta": {
    "total": 1
  }
}


⸻

5. Subscriptions

POST /api/v1/subscriptions

Request:

{
  "customer_account_id": "uuid",
  "service_plan_id": "uuid"
}


⸻

6. Invoices

POST /api/v1/billing-invoices

Request:

{
  "customer_account_id": "uuid",
  "lines": [
    {
      "description": "Monthly fee",
      "quantity": "1",
      "unit_price": "99.00"
    }
  ]
}


⸻

GET /api/v1/billing-invoices/{id}

Response:

{
  "data": {
    "id": "uuid",
    "total_amount": "99.00",
    "status": "open"
  }
}


⸻

7. Payments

POST /api/v1/payments

Request:

{
  "invoice_id": "uuid",
  "amount": "50.00"
}

Response:

{
  "data": {
    "status": "succeeded"
  }
}


⸻

8. Notifications

GET /api/v1/notifications

Response:

{
  "data": [
    {
      "id": "uuid",
      "status": "sent"
    }
  ]
}


⸻

9. Support

POST /api/v1/support

Request:

{
  "subject": "Missing document",
  "description": "Driver did not upload BOL"
}


⸻

Pagination contract

Query:

?page=1&page_size=25

Response:

{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 0
  }
}


⸻

Error contract

All errors follow:

{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}


⸻

Validation errors

Example:

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field required"
  }
}


⸻

Future enhancements
	•	strict schema validation
	•	OpenAPI-driven contracts
	•	SDK generation
	•	versioned contract changes

⸻

Summary

Endpoint contracts define:
	•	how requests are structured
	•	how responses are returned
	•	how errors are handled

They ensure the API remains predictable, stable, and easy to integrate.

---

## Next file (aligned with your structure)

```text
docs/api/webhook-contracts.md