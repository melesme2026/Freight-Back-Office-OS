# System Overview

## Purpose

Freight Back Office OS is an operational platform for freight companies, dispatch teams, and family-run trucking businesses that need to manage paperwork, load readiness, customer onboarding, billing, and support in one system.

The system is designed to reduce manual back-office work currently handled across WhatsApp, email, phone calls, spreadsheets, and disconnected billing tools.

## What problem the system solves

In a legacy workflow, an operator or family member usually has to:

- receive rate confirmations, BOLs, PODs, and invoices from drivers
- manually rename and organize files
- check whether load paperwork is complete
- compare extracted values by eye
- follow up with drivers for missing documents
- decide when a load is ready for invoice submission
- track customer readiness and onboarding steps
- send reminders and updates manually
- prepare invoices and track payments in separate systems

Freight Back Office OS centralizes that workflow into a structured operating system.

## Core system capabilities

The platform is organized around the following major capabilities:

### 1. Multi-channel ingestion

The system accepts operational inputs from multiple channels:

- WhatsApp
- email
- API/webhooks
- manual upload

This allows the business to keep using familiar communication channels while bringing all incoming data into a controlled internal workflow.

### 2. Document management

Documents are stored and tracked as first-class records. Supported freight document categories include:

- rate confirmations
- bills of lading
- proofs of delivery
- invoices
- unknown/unclassified supporting files

Each document can be linked to a load, driver, customer account, and source channel.

### 3. Extraction and validation

The platform supports AI-assisted and rule-based document handling through:

- OCR text extraction
- document classification
- field extraction
- confidence scoring
- anomaly detection
- business validation rules

Examples of validation include:

- missing required fields
- missing signatures
- amount mismatches
- broker inconsistencies
- duplicate load detection
- unreadable document detection

### 4. Load lifecycle control

Loads move through an explicit workflow state machine instead of informal spreadsheet status updates.

Examples of states include:

- new
- docs received
- extracting
- needs review
- validated
- ready to submit
- submitted
- funded
- paid
- exception
- archived

This creates operational visibility and traceability across the full lifecycle.

### 5. Review queue and human correction

When automation is uncertain or a business rule fails, the system routes work into a review queue where staff can:

- review extracted data
- correct fields
- resolve validation issues
- mark a load as reviewed

This allows human-in-the-loop operations instead of full blind automation.

### 6. Customer onboarding

The platform tracks onboarding readiness for each customer account, including:

- documents received
- pricing confirmed
- payment method added
- driver profiles created
- channel connected
- go-live readiness

This replaces ad hoc onboarding tracking done in messages or spreadsheets.

### 7. Billing and revenue operations

The billing domain supports:

- service plans
- subscriptions
- usage records
- invoice generation
- payment collection
- ledger entries
- overdue handling and reminder workflows

This allows the business to evolve from manual invoicing into a structured SaaS-style back-office business model.

### 8. Notifications and support

The system also includes:

- outbound/inbound notification records
- channel-aware messaging services
- support ticket intake
- support routing
- audit history

This supports both internal operations and external customer communications.

## High-level architecture

The platform follows a layered architecture.

### API layer

The API layer exposes versioned routes for operational modules such as:

- auth
- organizations
- customer accounts
- onboarding
- referrals
- drivers
- brokers
- loads
- documents
- review queue
- notifications
- billing
- support
- health
- webhooks

### Service layer

The service layer contains orchestration logic and business behavior such as:

- creating and updating loads
- classifying documents
- extracting fields
- validating loads
- transitioning workflow states
- generating invoices
- collecting payments
- routing tickets
- sending notifications

### Repository layer

Repositories isolate persistence operations for domain entities and provide structured access to:

- create
- retrieve
- list
- update
- delete

This keeps data access separate from business rules.

### Domain model layer

The domain model defines the core entities such as:

- organization
- customer account
- driver
- broker
- load
- document
- extracted field
- validation issue
- workflow event
- notification
- service plan
- subscription
- invoice
- payment
- ledger entry
- support ticket
- api client

### Worker layer

Celery-based workers are used for asynchronous and scheduled work such as:

- document processing
- classification
- field extraction
- validation
- notification sending
- recurring invoice generation
- overdue invoice marking
- payment webhook sync

### Storage and infrastructure layer

The system is designed to work with:

- PostgreSQL for primary persistence
- Redis for queueing and worker coordination
- local or object storage for file persistence
- Docker Compose for local orchestration
- Alembic for migrations
- future Kubernetes/container deployment support

## Domain boundaries

The major domain boundaries are:

- **Tenant and identity**: organizations, staff users, api clients
- **Commercial relationships**: customer accounts, referrals, onboarding
- **Operations**: drivers, brokers, loads, workflow events
- **Documents and AI**: load documents, extracted fields, validation issues
- **Communications**: notifications, inbound/outbound messages
- **Billing**: service plans, subscriptions, usage records, invoices, payments, ledger
- **Support and compliance**: support tickets, audit logs

## Primary operational flow

A typical V1 flow looks like this:

1. A driver sends paperwork through WhatsApp, email, or manual upload.
2. The system creates a document record.
3. The document is classified and processed.
4. OCR and extraction generate structured fields.
5. Validation rules detect missing or conflicting information.
6. The load is linked or updated.
7. If issues exist, the load enters the review queue.
8. A staff member reviews and corrects data if needed.
9. The load advances through workflow states.
10. Once operationally complete, billing and invoice generation can occur.
11. Payments and account activity are tracked.
12. Notifications and support actions are recorded for traceability.

## Non-functional goals

The platform is being designed with these goals:

- production-grade architecture
- explicit workflow control
- strong auditability
- modular service design
- multi-tenant readiness
- replaceability of placeholder AI components
- readiness for eventual SaaS commercialization
- support for family-scale operations first, enterprise scale later

## Current maturity

The current repository provides the structural and architectural foundation. Some modules still use placeholder logic, especially around:

- OCR
- LLM extraction
- anomaly detection
- notification delivery
- ingestion normalization
- worker task internals

That is intentional for the current build stage. The structure is being established first so business-specific rules and real operational data can be added safely later.

## Future evolution

As real documents and workflows are collected from the business, the next evolution of the system should include:

- real freight document samples and field maps
- more accurate document classification
- production OCR and extraction pipelines
- stronger load matching and reconciliation
- billing automation tied to real contracts
- richer dashboards and operator UI
- role-based permissions
- production observability and deployment pipelines

## Summary

Freight Back Office OS is the operating backbone for turning freight paperwork, driver communications, customer onboarding, and billing activity into a structured, auditable, scalable system.

Its purpose is not just to store documents. Its purpose is to run the freight back office.