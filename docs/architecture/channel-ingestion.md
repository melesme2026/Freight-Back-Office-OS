docs/architecture/channel-ingestion.md

# Channel Ingestion

## Purpose

This document defines how external data enters Freight Back Office OS.

It covers:

- supported ingestion channels
- ingestion architecture
- how messages and documents are processed
- normalization strategy
- future expansion

---

## Why channel ingestion matters

In real freight operations, data does not arrive in a clean, structured format.

Instead, it comes from:

- WhatsApp messages from drivers
- email attachments
- API integrations
- manual uploads

The system must:

- accept all of these inputs
- normalize them
- convert them into structured internal records

---

## Supported channels

### Current (V1 foundation)

- manual upload (primary)
- WhatsApp webhook (placeholder)

---

### Planned

- email ingestion
- API ingestion
- partner integrations

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


⸻

Ingestion architecture

Located under:

backend/app/services/ingestion/

Key components:
	•	ingestion_router.py
	•	channel_dispatcher.py
	•	upload_service.py
	•	whatsapp_ingestion_service.py
	•	email_ingestion_service.py
	•	api_ingestion_service.py

⸻

1. Ingestion Router

File:

ingestion_router.py

Role
	•	entry point for all ingestion flows
	•	receives incoming payloads
	•	determines channel
	•	routes to dispatcher

⸻

2. Channel Dispatcher

File:

channel_dispatcher.py

Role
	•	selects correct ingestion service based on channel
	•	abstracts channel-specific logic

Example:

channel = whatsapp → whatsapp_ingestion_service
channel = email → email_ingestion_service
channel = api → api_ingestion_service


⸻

3. Upload Service (manual ingestion)

File:

upload_service.py

Role
	•	handles direct file uploads
	•	stores files locally or in storage backend
	•	creates document records
	•	links documents to loads if possible

⸻

4. WhatsApp ingestion service

File:

whatsapp_ingestion_service.py

Role
	•	process WhatsApp webhook payloads
	•	extract sender (driver phone)
	•	extract message content
	•	extract attachments
	•	create document or message records

⸻

Expected behavior
	•	map phone number → driver
	•	store raw payload
	•	download media if present
	•	create document record
	•	trigger processing pipeline

⸻

5. Email ingestion service

File:

email_ingestion_service.py

Role
	•	process email webhook payloads
	•	extract sender, subject, attachments
	•	download attachments
	•	create document records

⸻

6. API ingestion service

File:

api_ingestion_service.py

Role
	•	handle programmatic ingestion from external systems
	•	accept structured payloads
	•	create documents or loads directly

⸻

Data normalization

Each channel has different formats.

The system must normalize them into a common structure.

⸻

Raw inputs

Examples:
	•	WhatsApp JSON payload
	•	email webhook payload
	•	file upload metadata

⸻

Normalized internal format

Document
  - file
  - source channel
  - metadata
  - linked entities (driver, load)


⸻

Linking logic

After ingestion, the system attempts to link documents to:
	•	driver (via phone/email)
	•	load (via extracted data or manual association)

⸻

Storage strategy

Files are stored using:

storage_service.py

V1:
	•	local filesystem storage

Future:
	•	object storage (S3, GCS, etc.)

⸻

Processing trigger

After ingestion:

Document created → enqueue processing tasks

Tasks include:
	•	classification
	•	OCR
	•	extraction
	•	validation

⸻

Idempotency

Webhook ingestion must be safe to retry.

Approach:
	•	track event IDs if available
	•	avoid duplicate document creation
	•	hash files to detect duplicates

⸻

Error handling

If ingestion fails:
	•	log error
	•	return accepted=false for webhook (optional)
	•	retry mechanism (future)

⸻

Security considerations
	•	validate incoming payload structure
	•	verify webhook signatures (future)
	•	restrict file types and size
	•	sanitize filenames
	•	prevent malicious uploads

⸻

V1 simplifications

In V1:
	•	WhatsApp parsing is basic
	•	email ingestion is placeholder
	•	no signature validation yet
	•	no advanced deduplication
	•	linking logic is simple

Focus is on getting documents into the system.

⸻

Future enhancements
	•	robust WhatsApp integration
	•	full email ingestion pipeline
	•	retry and replay mechanisms
	•	ingestion monitoring dashboard
	•	document deduplication improvements
	•	smart load matching at ingestion time

⸻

Design principles
	•	channel-agnostic internal model
	•	modular ingestion services
	•	separation of ingestion and processing
	•	safe retry behavior
	•	auditability of raw inputs

⸻

Summary

Channel ingestion is the entry point of the entire system.

It ensures that:
	•	all external inputs are accepted
	•	data is normalized
	•	documents are created reliably
	•	processing pipelines are triggered

It is critical for connecting real-world operations to the system.

