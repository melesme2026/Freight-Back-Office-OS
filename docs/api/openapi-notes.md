Paste this into:

docs/api/openapi-notes.md

# OpenAPI Notes

## Purpose

This document explains how the API is structured, documented, and exposed using OpenAPI (Swagger) in Freight Back Office OS.

It serves as a guide for:

- backend developers
- frontend developers
- integration partners
- API consumers

---

## API base structure

All API routes are versioned:

```text
/api/v1

Example:

GET /api/v1/health
GET /api/v1/loads
POST /api/v1/documents


⸻

OpenAPI endpoints

FastAPI automatically exposes:

Swagger UI

/api/v1/docs

Interactive API explorer.

⸻

ReDoc

/api/v1/redoc

Structured API documentation view.

⸻

OpenAPI JSON

/api/v1/openapi.json

Machine-readable API spec.

⸻

API design principles

1. Versioned APIs

All endpoints must be under:

/api/v1

Future versions:

/api/v2


⸻

2. Resource-based routing

Examples:

GET    /loads
POST   /loads
GET    /loads/{id}
PATCH  /loads/{id}


⸻

3. Consistent naming
	•	plural resource names
	•	snake_case fields
	•	predictable URL patterns

⸻

4. Separation of concerns

Each module has its own route file:
	•	loads.py
	•	documents.py
	•	billing_invoices.py
	•	payments.py
	•	support.py

⸻

Response format

Standard pattern:

{
  "data": {},
  "meta": {},
  "error": null
}


⸻

Success example

{
  "data": {
    "id": "123",
    "status": "validated"
  }
}


⸻

Error example

{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Missing required fields"
  }
}


⸻

Pagination

List endpoints should support:

?page=1&page_size=25

Response:

{
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 100
  }
}


⸻

Filtering and querying

Example:

GET /loads?status=validated
GET /invoices?status=past_due


⸻

Request validation

All requests use Pydantic schemas.

Example:

class CreateLoadRequest(BaseModel):
    load_number: str
    gross_amount: Decimal


⸻

Response schemas

Every endpoint should return a defined schema.

Benefits:
	•	consistency
	•	validation
	•	frontend integration safety

⸻

Error handling

Use structured errors:
	•	HTTP status codes
	•	standardized error payload

Examples:

Code	Meaning
400	Bad request
401	Unauthorized
404	Not found
422	Validation error
500	Internal error


⸻

Authentication (future)

Planned:
	•	JWT-based auth
	•	role-based access control
	•	API key support for integrations

⸻

Webhooks

Separate endpoints for:
	•	WhatsApp ingestion
	•	Email ingestion
	•	Payment provider callbacks

Example:

POST /api/v1/webhooks/whatsapp
POST /api/v1/webhooks/payment


⸻

Documentation best practices

When adding a new endpoint:
	•	define request schema
	•	define response schema
	•	add summary + description
	•	include examples
	•	test in Swagger UI

⸻

Testing API

Use:
	•	Swagger UI (/docs)
	•	Postman / Bruno
	•	curl

Example:

curl http://localhost:8000/api/v1/health


⸻

Future improvements
	•	full OpenAPI contract enforcement
	•	client SDK generation
	•	API version deprecation strategy
	•	rate limiting
	•	request tracing

⸻

Summary

The OpenAPI layer ensures:
	•	clear API contracts
	•	easy integration
	•	consistent structure
	•	discoverable endpoints

It is the foundation for frontend and external integrations.

---

## Next file (aligned with your structure)

```text
docs/api/endpoint-contracts.md