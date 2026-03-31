# Endpoint Contracts

## Purpose

This document defines the expected request and response contracts for core API endpoints.

It ensures:

* consistency across services
* clear frontend-backend integration
* predictable behavior for consumers

---

## Standard response format

All endpoints should follow this envelope where applicable:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

Notes:

* `data` contains the primary response payload.
* `meta` is optional and is typically used for pagination or supplemental response metadata.
* `error` is `null` on success and populated on failure.

---

## Success response

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

---

## Error response

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

## Authentication (future)

Headers:

```text
Authorization: Bearer <token>
```

---

## Core endpoint groups

### 1. Health

#### `GET /api/v1/health`

Response:

```json
{
  "data": {
    "status": "ok"
  },
  "meta": {},
  "error": null
}
```

---

### 2. Loads

#### `POST /api/v1/loads`

Request:

```json
{
  "load_number": "LOAD-1001",
  "gross_amount": "1200.00"
}
```

Response:

```json
{
  "data": {
    "id": "uuid",
    "status": "new"
  },
  "meta": {},
  "error": null
}
```

#### `GET /api/v1/loads/{id}`

Response:

```json
{
  "data": {
    "id": "uuid",
    "status": "validated",
    "gross_amount": "1200.00"
  },
  "meta": {},
  "error": null
}
```

#### `PATCH /api/v1/loads/{id}`

Request:

```json
{
  "status": "validated"
}
```

---

### 3. Documents

#### `POST /api/v1/documents`

Request (`multipart/form-data`):

* `file`
* `metadata` (optional)

Response:

```json
{
  "data": {
    "id": "uuid",
    "status": "pending"
  },
  "meta": {},
  "error": null
}
```

#### `GET /api/v1/documents/{id}`

Response:

```json
{
  "data": {
    "id": "uuid",
    "document_type": "invoice",
    "processing_status": "completed"
  },
  "meta": {},
  "error": null
}
```

---

### 4. Review Queue

#### `GET /api/v1/review-queue`

Response:

```json
{
  "data": [
    {
      "load_id": "uuid",
      "issues": ["missing_signature"]
    }
  ],
  "meta": {
    "total": 1
  },
  "error": null
}
```

---

### 5. Subscriptions

#### `POST /api/v1/subscriptions`

Request:

```json
{
  "customer_account_id": "uuid",
  "service_plan_id": "uuid"
}
```

---

### 6. Invoices

#### `POST /api/v1/billing-invoices`

Request:

```json
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
```

#### `GET /api/v1/billing-invoices/{id}`

Response:

```json
{
  "data": {
    "id": "uuid",
    "total_amount": "99.00",
    "status": "open"
  },
  "meta": {},
  "error": null
}
```

---

### 7. Payments

#### `POST /api/v1/payments`

Request:

```json
{
  "invoice_id": "uuid",
  "amount": "50.00"
}
```

Response:

```json
{
  "data": {
    "status": "succeeded"
  },
  "meta": {},
  "error": null
}
```

---

### 8. Notifications

#### `GET /api/v1/notifications`

Response:

```json
{
  "data": [
    {
      "id": "uuid",
      "status": "sent"
    }
  ],
  "meta": {},
  "error": null
}
```

---

### 9. Support

#### `POST /api/v1/support`

Request:

```json
{
  "subject": "Missing document",
  "description": "Driver did not upload BOL"
}
```

---

## Pagination contract

Query:

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
    "total": 0
  },
  "error": null
}
```

---

## Error contract

All errors should follow:

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

---

## Validation errors

Example:

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field required"
  }
}
```

---

## Future enhancements

* strict schema validation
* OpenAPI-driven contracts
* SDK generation
* versioned contract changes

---

## Summary

Endpoint contracts define:

* how requests are structured
* how responses are returned
* how errors are handled

They help keep the API predictable, stable, and easy to integrate.
