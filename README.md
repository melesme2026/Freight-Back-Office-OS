# Freight Back Office OS

Enterprise-grade back-office operating system for freight and dispatch teams, designed to centralize document intake, load lifecycle tracking, validation, billing, onboarding, notifications, and support workflows.

---

## Vision

Freight Back Office OS is built to replace fragmented manual back-office work such as:

* collecting rate confirmations, BOLs, and invoices over WhatsApp, email, and manual uploads
* manually checking document completeness and payout readiness
* tracking driver paperwork in spreadsheets or chat threads
* managing customer onboarding and support in disconnected tools
* handling billing, subscriptions, invoices, and payment reconciliation with limited automation

The platform provides a structured operational system that can evolve from a small family-run trucking workflow into a production-grade multi-tenant SaaS platform.

---

## Core Scope

This repository currently includes a production-oriented backend foundation with:

* FastAPI application structure
* SQLAlchemy domain model layout
* repository and service layer patterns
* workflow engine and validation rules
* document ingestion and placeholder OCR / extraction services
* billing, subscriptions, invoices, payments, and ledger services
* onboarding, referrals, notifications, and support modules
* Celery worker scaffolding and scheduled job placeholders
* API routes for core operational entities
* unit and integration test scaffolding

---

## High-Level Architecture

The backend is organized around the following domains:

* **Organizations** – tenant boundary for customers and operations
* **Customer Accounts** – freight customers and business accounts
* **Drivers** – driver records and related load activity
* **Brokers** – broker master records and commercial metadata
* **Loads** – shipment lifecycle tracking
* **Documents** – rate confirmations, BOLs, PODs, invoices
* **Extraction & Validation** – OCR + rule-based validation
* **Workflow** – load state transitions and history
* **Notifications** – operational communication
* **Onboarding** – customer activation lifecycle
* **Billing** – subscriptions, invoices, payments, ledger
* **Support** – ticket intake and resolution
* **Audit** – system-wide event tracking

---

## Repository Structure

```text
backend/
  app/
    api/
    core/
    domain/
    repositories/
    schemas/
    services/
    utils/
    workers/
  tests/
docs/
frontend/
infra/
shared/
data/
```

---

## Backend Stack

* Python
* FastAPI
* SQLAlchemy ORM
* Pydantic
* Celery
* PostgreSQL-ready schema design
* Redis (broker + caching)
* pytest

---

## API Surface

Base path:

```text
/api/v1
```

Route groups:

* auth
* organizations
* customer accounts
* onboarding
* referrals
* staff users
* drivers
* brokers
* loads
* documents
* review queue
* dashboard
* notifications
* service plans
* subscriptions
* billing invoices
* payments
* billing dashboard
* support
* webhooks
* health

---

## Development Status

### Already Implemented

* enterprise-grade folder structure
* domain model coverage
* repository layer
* service orchestration
* API route scaffolding
* placeholder OCR / ingestion / notification logic
* workflow and validation patterns
* test scaffolding

### Next Steps

* finalize SQLAlchemy relationships and enums
* add Alembic migrations
* harden middleware and exception handling
* enforce request/response schemas
* replace placeholder AI/OCR services
* implement file storage and streaming
* enforce authentication and authorization
* build frontend dashboards
* implement billing automation and webhooks
* add CI/CD and deployment packaging

---

## Local Development

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

Activate:

```bash
# Windows
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

---

### 2. Install Dependencies

```bash
pip install -e .[dev]
```

---

### 3. Configure Environment

Create `.env` in repo root:

```env
APP_ENV=local
DATABASE_URL=sqlite+pysqlite:///./freight_back_office.db
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
```

---

### 4. Run Backend

```bash
cd backend
uvicorn app.main:app --reload
```

---

### 5. Access API

```text
http://127.0.0.1:8000/api/v1/docs
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/api/v1/health/ready
```

---

## Running Tests

```bash
cd backend
pytest
```

---

## Operational Problem This Solves

### Legacy Workflow

Typical freight back-office operations involve:

* receiving documents via WhatsApp/email
* manual file handling
* manual validation and comparison
* spreadsheet tracking
* chasing missing documents
* manual invoicing and reconciliation
* fragmented support communication

### Solution

Freight Back Office OS provides:

* centralized document ingestion
* automated classification and linking
* AI-assisted data extraction
* rule-based validation
* workflow automation
* billing and ledger tracking
* onboarding and support visibility
* audit trails and reporting

---

## Design Principles

* production-first architecture
* explicit domain modeling
* strict separation of concerns
* workflow-driven system behavior
* multi-tenant readiness
* auditability and traceability
* incremental AI integration

---

## Important Note

This project is **structurally production-ready**, but several modules still contain placeholder implementations that will be replaced in later phases.

This is intentional at this stage.

---

## Recommended Milestones

1. stabilize core configuration and middleware
2. validate database schema end-to-end
3. implement Alembic migrations
4. enforce typed API contracts
5. implement document storage pipeline
6. integrate OCR + AI extraction
7. add authentication and permissions
8. build frontend + dashboards
9. complete billing + webhook flows
10. deploy with CI/CD

---

## License

Proprietary and private internal project unless explicitly relicensed.
