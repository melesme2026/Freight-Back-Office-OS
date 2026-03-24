# Freight Back Office OS — V1 Scope

## Overview

Freight Back Office OS is a production-grade system designed to automate the back-office operations of small to mid-sized trucking businesses.

The system ingests real-world freight documents (Rate Confirmations, Bills of Lading, Invoices), extracts structured data using AI, validates cross-document consistency, and enables operational workflows such as invoicing and payment tracking.

This is not a demo system. It is designed to support real business operations and scale over time.

---

## Core Objective

Enable a driver or dispatcher to:

1. Submit load documents (via manual upload or future WhatsApp ingestion)
2. Automatically extract key freight data
3. Validate document consistency
4. Track load lifecycle
5. Generate invoice-ready data
6. Monitor payment status

---

## Supported Document Types (V1)

- Rate Confirmation (RateCon)
- Bill of Lading (BOL)
- Invoice

---

## Core System Flow (V1)

1. Load is created (manual or system-generated)
2. Documents are uploaded and linked to the load
3. AI extraction runs on each document
4. Extracted data is stored with confidence scores
5. Validation engine compares documents
6. Load status progresses through workflow
7. Load becomes invoice-ready
8. Payment lifecycle begins

---

## Load Lifecycle (High-Level)

- CREATED
- DOCUMENTS_PENDING
- PROCESSING
- VALIDATED
- READY_FOR_INVOICING
- INVOICED
- FUNDED
- PAID

---

## Core Entities

### Load
Represents a freight job.

Key attributes:
- organization_id
- driver_id
- customer_account_id
- broker_id
- load_number
- status
- processing_status
- gross_amount
- currency_code
- documents_complete
- timestamps (created, updated, submitted, funded, paid)

---

### Document
Represents an uploaded file tied to a load.

Types:
- rate_confirmation
- bol
- invoice

Key attributes:
- load_id
- document_type
- file_path / storage reference
- upload_source (manual / WhatsApp future)
- processing_status
- extraction_status

---

### Extraction Result
Represents AI output.

- document_id
- extracted_json
- confidence_score
- field-level confidence
- processed_at

---

### Validation Result
Represents cross-document validation.

- load_id
- validation_status
- consistency checks
- blocking issues
- review flags
- auto-approval eligibility

---

## AI Responsibilities (V1)

1. Extract structured data from each document type
2. Assign confidence scores per field
3. Normalize key fields (dates, amounts)
4. Validate cross-document consistency
5. Identify missing or conflicting information

---

## Validation Logic (V1)

Key checks:
- load_number consistency
- bol_number consistency
- rate_confirmation_number consistency
- pickup/delivery dates alignment
- pickup/delivery locations alignment
- broker/carrier consistency
- gross amount consistency

Outputs:
- validation_status
- blocking issues
- review flags
- auto-approval recommendation

---

## API Capabilities (V1)

### Load APIs
- Create load
- List loads (with filters)
- Get load details
- Update load
- Transition load status

### Document APIs (Next Phase)
- Upload document
- List documents per load
- Trigger extraction
- Get extraction results

---

## Processing Status (V1)

Per load:
- NOT_STARTED
- IN_PROGRESS
- COMPLETED
- FAILED

Per document:
- UPLOADED
- PROCESSING
- EXTRACTED
- VALIDATED
- FAILED

---

## Operational Rules (V1)

- A load is not “ready” until required documents are present
- Missing documents reduce automation capability but do not block ingestion
- Conflicting data requires manual review
- High-confidence matches can enable auto-approval (future)

---

## Out of Scope (V1)

- Payments processing (actual money movement)
- Advanced analytics dashboards
- Multi-tenant billing logic
- Driver mobile app UI
- Real-time notifications
- OCR engine implementation (assumed external or pre-processed input)

---

## Future (Post-V1)

- WhatsApp ingestion (image → load auto-create)
- Auto-invoice generation (PDF)
- Factoring integration
- Payment tracking automation
- Driver portal
- Broker integrations
- Fraud detection
- ML-based anomaly detection

---

## Success Criteria

- A load can be created and fully processed end-to-end
- Documents can be uploaded and linked
- AI extraction produces structured, usable data
- Validation identifies inconsistencies
- System determines invoice readiness
- Data is reliable enough for real operational use

---

## Guiding Principle

Build for real-world trucking workflows first.

Accuracy > automation  
Clarity > complexity  
Reliability > speed