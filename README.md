# Freight Back Office OS

Enterprise-grade back-office operating system for freight and dispatch teams, designed to centralize document intake, load lifecycle tracking, validation, billing, onboarding, notifications, and support workflows.

## Vision

Freight Back Office OS is built to replace fragmented manual back-office work such as:

- collecting rate confirmations, BOLs, and invoices over WhatsApp, email, and manual uploads
- manually checking document completeness and payout readiness
- tracking driver paperwork in spreadsheets or chat threads
- managing customer onboarding and support in disconnected tools
- handling billing, subscriptions, invoices, and payment reconciliation with limited automation

The platform provides a structured operational system that can evolve from a small family-run trucking workflow into a production-grade multi-tenant SaaS platform.

## Core scope

This repository currently includes a production-oriented backend foundation with:

- FastAPI application structure
- SQLAlchemy domain model layout
- repositories and service layer patterns
- workflow engine and validation rules
- document ingestion and placeholder OCR / extraction services
- billing, subscriptions, invoices, payments, and ledger services
- onboarding, referrals, notifications, and support modules
- Celery worker scaffolding and scheduled job placeholders
- API routes for core operational entities
- unit and integration test scaffolding

## High-level architecture

The current backend is organized around these domains:

- **Organizations**: tenant boundary for customers and operations
- **Customer Accounts**: freight customers / business accounts
- **Drivers**: driver records and related load activity
- **Brokers**: broker master records and commercial metadata
- **Loads**: core operational record representing shipment lifecycle
- **Documents**: uploaded paperwork such as rate cons, BOLs, PODs, invoices
- **Extraction & Validation**: AI / OCR assisted field extraction and business rule checks
- **Workflow**: load state transitions and workflow event history
- **Notifications**: outbound or inbound operational communications
- **Onboarding**: go-live readiness tracking for customer accounts
- **Billing**: service plans, subscriptions, invoices, payments, usage, ledger
- **Support**: support ticket intake and routing
- **Audit**: auditable event tracking across the platform

## Current repository structure

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

Backend stack
	•	Python
	•	FastAPI
	•	SQLAlchemy ORM
	•	Pydantic
	•	Celery
	•	PostgreSQL-ready schema design
	•	Redis / broker-ready worker configuration
	•	pytest

Current API surface

The backend exposes versioned routes under:

/api/v1

Current route groups include:
	•	auth
	•	organizations
	•	customer accounts
	•	onboarding
	•	referrals
	•	staff users
	•	drivers
	•	brokers
	•	loads
	•	documents
	•	review queue
	•	dashboard
	•	notifications
	•	service plans
	•	subscriptions
	•	billing invoices
	•	payments
	•	billing dashboard
	•	support
	•	webhooks
	•	health

Development status

This project is currently in a foundational build stage.

What is already in place:
	•	enterprise-style folder structure
	•	initial domain model coverage
	•	repositories for major entities
	•	service-layer orchestration patterns
	•	route scaffolding for core API areas
	•	placeholder ingestion, OCR, extraction, notification, and worker logic
	•	validation rules and workflow transition patterns
	•	test scaffolding across unit and integration levels

What still needs to be completed next:
	•	normalize and verify all model relationships and enum usage end-to-end
	•	finalize database compatibility for PostgreSQL and SQLite test modes
	•	add Alembic migrations
	•	complete exception handling and middleware behavior
	•	harden request / response contracts
	•	replace placeholder OCR / LLM services with real implementations
	•	add file upload streaming and object storage support
	•	add authentication / authorization enforcement across all routes
	•	implement frontend and operator dashboards
	•	add full billing automation and webhook reconciliation
	•	package deployment and CI/CD workflows

Local development

1. Create a virtual environment

python -m venv .venv

Activate it:

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

2. Install dependencies

At minimum, install the backend stack required by the current codebase:

pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-jose passlib[bcrypt] celery pytest

If you are using PostgreSQL locally, also install:

pip install psycopg[binary]

If you are using SQLite for local experimentation, no extra driver is required.

3. Set environment variables

Create a .env file or export variables such as:

APP_ENV=local
DATABASE_URL=sqlite+pysqlite:///./freight_back_office.db
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://

Additional settings can be added as the configuration layer expands.

4. Run the API

From the backend directory:

uvicorn app.main:app --reload

5. Open the API

Once running locally, the API base should be available at:

http://127.0.0.1:8000/api/v1

Health endpoints:

GET /api/v1/health
GET /api/v1/health/ready

Running tests

From the backend directory:

pytest

Operational problem this system solves

Legacy manual process

In a typical small freight back-office workflow, a dispatcher or family member often has to:
	•	receive rate confirmations and BOLs through WhatsApp or email
	•	manually rename or organize files
	•	inspect documents one by one
	•	compare values across paperwork
	•	track load status in spreadsheets
	•	remind drivers for missing documents
	•	decide when an invoice is ready to send
	•	manually track who owes what and when payment arrives
	•	handle support issues in chat messages or phone calls

This creates delays, inconsistency, and operational blind spots.

What Freight Back Office OS does

The system is designed to:
	•	ingest documents from multiple channels
	•	classify and attach them to the right load
	•	extract important fields automatically
	•	validate the paperwork against business rules
	•	route exceptions into review queues
	•	move loads through a controlled workflow
	•	track onboarding and support activity
	•	generate invoices and collect billing data
	•	provide structured dashboards and audit history

Design principles
	•	production-oriented architecture
	•	explicit domain modeling
	•	separation of API, service, repository, and model layers
	•	clear workflow state control
	•	multi-tenant readiness
	•	auditable operations
	•	gradual replacement of placeholders with real AI and automation components

Important note

This repository currently contains a strong structural foundation, but several modules still use placeholder implementations intended to be replaced during the next build phases.

That is expected at this stage.

Recommended next milestones
	1.	stabilize core configuration, middleware, database, and exception behavior
	2.	verify all SQLAlchemy relationships and metadata creation end-to-end
	3.	add Alembic migrations for the current domain
	4.	make route contracts consistently use typed schema responses
	5.	wire real upload handling and document persistence
	6.	implement real OCR / extraction pipeline
	7.	add authentication and permission checks
	8.	build the operator frontend and driver portal
	9.	harden billing flows and payment webhooks
	10.	package for deployment with CI/CD

License

Proprietary / private internal project unless explicitly relicensed by the repository owner.

After you commit that, the next file is:

```text
.gitignore