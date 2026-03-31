# Channel Ingestion

## Purpose

This document defines how external data enters Freight Back Office OS.

It covers:

* supported ingestion channels
* ingestion architecture
* how messages and documents are processed
* normalization strategy
* future expansion

---

## Why channel ingestion matters

In real freight operations, data rarely arrives in a clean, structured format.

Instead, it comes from:

* WhatsApp messages from drivers
* email attachments
* API integrations
* manual uploads

The system must:

* accept these inputs
* normalize them
* convert them into structured internal records

---

## Supported channels

### Current (V1 foundation)

* manual upload (primary)
* WhatsApp webhook (placeholder)

### Planned

* email ingestion
* API ingestion
* partner integrations

---

## Core ingestion flow

```text
External Input
    ↓
Webhook / Upload Endpoint
    ↓
Ingestion Router
    ↓
Channel Dispatcher
    ↓
Ingestion Service (channel-specific)
    ↓
Document / Message Record Created
    ↓
Trigger Processing Pipeline
```

---

## Ingestion architecture

Located under:

```text
backend/app/services/ingestion/
```

Key components:

* `ingestion_router.py`
* `channel_dispatcher.py`
* `upload_service.py`
* `whatsapp_ingestion_service.py`
* `email_ingestion_service.py`
* `api_ingestion_service.py`

---

## 1. Ingestion Router

File:

```text
ingestion_router.py
```

Role:

* entry point for all ingestion flows
* receives incoming payloads
* determines channel
* routes to the dispatcher

---

## 2. Channel Dispatcher

File:

```text
channel_dispatcher.py
```

Role:

* selects the correct ingestion service based on channel
* abstracts channel-specific logic

Example:

```text
channel = whatsapp -> whatsapp_ingestion_service
channel = email -> email_ingestion_service
channel = api -> api_ingestion_service
```

---

## 3. Upload Service (manual ingestion)

File:

```text
upload_service.py
```

Role:

* handles direct file uploads
* stores files locally or in the storage backend
* creates document records
* links documents to loads if possible

---

## 4. WhatsApp ingestion service

File:

```text
whatsapp_ingestion_service.py
```

Role:

* processes WhatsApp webhook payloads
* extracts sender information, typically the driver phone number
* extracts message content
* extracts attachments
* creates document or message records

Expected behavior:

* map phone number to driver when possible
* store the raw payload
* download media if present
* create a document record
* trigger the processing pipeline

---

## 5. Email ingestion service

File:

```text
email_ingestion_service.py
```

Role:

* processes email webhook payloads
* extracts sender, subject, and attachments
* downloads attachments
* creates document records

---

## 6. API ingestion service

File:

```text
api_ingestion_service.py
```

Role:

* handles programmatic ingestion from external systems
* accepts structured payloads
* creates documents or loads directly

---

## Data normalization

Each channel has different input formats.

The system should normalize them into a common internal structure.

### Raw inputs

Examples:

* WhatsApp JSON payload
* email webhook payload
* file upload metadata

### Normalized internal format

```text
Document
  - file
  - source channel
  - metadata
  - linked entities (driver, load)
```

---

## Linking logic

After ingestion, the system attempts to link documents to:

* driver, using phone number or email when available
* load, using extracted data or manual association

---

## Storage strategy

Files are stored through:

```text
storage_service.py
```

V1:

* local filesystem storage

Future:

* object storage such as S3 or GCS

---

## Processing trigger

After ingestion:

```text
Document created -> enqueue processing tasks
```

Typical tasks include:

* classification
* OCR
* extraction
* validation

---

## Idempotency

Webhook ingestion must be safe to retry.

Approach:

* track event IDs when available
* avoid duplicate document creation
* hash files to detect duplicates

---

## Error handling

If ingestion fails:

* log the error
* optionally return `accepted=false` for webhooks where appropriate
* support retry mechanisms in a future phase

---

## Security considerations

* validate incoming payload structure
* verify webhook signatures in a future phase
* restrict file types and size
* sanitize filenames
* prevent malicious uploads

---

## V1 simplifications

In V1:

* WhatsApp parsing is basic
* email ingestion is placeholder-level
* no signature validation yet
* no advanced deduplication yet
* linking logic remains simple

The immediate focus is getting documents into the system reliably.

---

## Future enhancements

* robust WhatsApp integration
* full email ingestion pipeline
* retry and replay mechanisms
* ingestion monitoring dashboard
* document deduplication improvements
* smarter load matching at ingestion time

---

## Design principles

* channel-agnostic internal model
* modular ingestion services
* separation of ingestion and processing
* safe retry behavior
* auditability of raw inputs

---

## Summary

Channel ingestion is the entry point of the entire system.

It helps ensure that:

* external inputs are accepted
* data is normalized
* documents are created reliably
* processing pipelines are triggered

It is critical for connecting real-world operations to the platform.
