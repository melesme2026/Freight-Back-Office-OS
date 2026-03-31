# OpenAPI Notes

## Purpose

This document explains how the API is structured, documented, and exposed using OpenAPI (Swagger) in Freight Back Office OS.

It serves as a guide for:

* backend developers
* frontend developers
* integration partners
* API consumers

---

## API base structure

All API routes are versioned under:

```text
/api/v1
```

Examples:

```text
GET /api/v1/health
GET /api/v1/loads
POST /api/v1/documents
```

---

## OpenAPI endpoints

FastAPI automatically exposes the following documentation endpoints.

### Swagger UI

```text
/api/v1/docs
```

Interactive API explorer.

### ReDoc

```text
/api/v1/redoc
```

Structured API documentation view.

### OpenAPI JSON

```text
/api/v1/openapi.json
```

Machine-readable API specification.

---

## API design principles

### 1. Versioned APIs

All endpoints must be under:

```text
/api/v1
```

Future versions may be introduced as:

```text
/api/v2
```

### 2. Resource-based routing

Examples:

```text
GET    /loads
POST   /loads
GET    /loads/{id}
PATCH  /loads/{id}
```

### 3. Consistent naming

* plural resource names
* snake_case fields
* predictable URL patterns

### 4. Separation of concerns

Each module should have its own route file, for example:

* `loads.py`
* `documents.py`
* `billing_invoices.py`
* `payments.py`
* `support.py`

---

## Response format

Standard pattern:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

### Success example

```json
{
  "data": {
    "id": "123",
    "status": "validated"
  },
  "meta": {},
  "error": null
}
```

### Error example

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Missing required fields"
  }
}
```

---

## Pagination

List endpoints should support:

```text
?page=1&page_size=25
```

Response:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 100
  },
  "error": null
}
```

---

## Filtering and querying

Examples:

```text
GET /loads?status=validated
GET /invoices?status=past_due
```

---

## Request validation

All requests should use Pydantic schemas.

Example:

```python
class CreateLoadRequest(BaseModel):
    load_number: str
    gross_amount: Decimal
```

---

## Response schemas

Every endpoint should return a defined schema.

Benefits:

* consistency
* validation
* frontend integration safety

---

## Error handling

Use structured errors with:

* HTTP status codes
* standardized error payloads

Examples:

| Code | Meaning          |
| ---- | ---------------- |
| 400  | Bad request      |
| 401  | Unauthorized     |
| 404  | Not found        |
| 422  | Validation error |
| 500  | Internal error   |

---

## Authentication (future)

Planned:

* JWT-based authentication
* role-based access control
* API key support for integrations

---

## Webhooks

Separate endpoints should exist for:

* WhatsApp ingestion
* email ingestion
* payment provider callbacks

Examples:

```text
POST /api/v1/webhooks/whatsapp
POST /api/v1/webhooks/payment
```

---

## Documentation best practices

When adding a new endpoint:

* define the request schema
* define the response schema
* add a summary and description
* include examples
* test in Swagger UI

---

## Testing the API

Use:

* Swagger UI (`/api/v1/docs`)
* Postman or Bruno
* `curl`

Example:

```bash
curl http://localhost:8000/api/v1/health
```

---

## Future improvements

* full OpenAPI contract enforcement
* client SDK generation
* API version deprecation strategy
* rate limiting
* request tracing

---

## Summary

The OpenAPI layer ensures:

* clear API contracts
* easy integration
* consistent structure
* discoverable endpoints

It is the foundation for frontend and external integrations.
