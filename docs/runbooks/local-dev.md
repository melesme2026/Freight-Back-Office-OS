Paste this into:

docs/runbooks/local-dev.md

# Local Development Runbook

## Purpose

This runbook explains how to run Freight Back Office OS locally for development, testing, and early workflow validation.

It covers:

- local prerequisites
- environment setup
- Docker-based startup
- manual backend startup
- workers and scheduler
- migrations
- tests
- common troubleshooting

---

## Repository assumptions

This runbook assumes the project root is:

```text
Freight-Back-Office-OS/

Key folders:

backend/
frontend/
infra/
docs/
data/


⸻

Prerequisites

Install the following first:
	•	Python 3.11+
	•	Node.js 20+
	•	Docker Desktop
	•	Git

Recommended:
	•	VS Code or IntelliJ
	•	Postman or Bruno
	•	pgAdmin or TablePlus

⸻

Environment file

Create a local .env in the project root.

Start from:

.env.example

Minimum local values:

APP_ENV=local
APP_NAME=Freight Back Office OS
APP_VERSION=0.1.0
DEBUG=true

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/freight_back_office_os
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
TIMEZONE=America/Toronto

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
STORAGE_LOCAL_ROOT_PATH=./data/sandbox/uploaded-docs


⸻

Option 1: Docker-based local stack

This is the recommended way to run the system because it keeps Postgres, Redis, API, worker, and beat aligned.

Start the stack

From project root:

docker compose up -d

Check running services

docker compose ps

Expected services:
	•	postgres
	•	redis
	•	api
	•	worker
	•	beat

View logs

API logs:

docker compose logs -f api

Worker logs:

docker compose logs -f worker

Beat logs:

docker compose logs -f beat

Stop the stack

docker compose down


⸻

Option 2: Manual local backend run

Use this when you want faster iteration without full Docker orchestration.

Create virtual environment

From project root:

python -m venv .venv

Activate it.

Windows PowerShell:

.venv\Scripts\Activate.ps1

macOS/Linux:

source .venv/bin/activate

Install backend dependencies

pip install -e .

If editable install gives trouble, install the main packages directly:

pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings celery redis psycopg[binary] alembic python-jose[cryptography] passlib[bcrypt] pytest

Run the backend API

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Run Celery worker

In a separate terminal:

cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info

Run Celery beat

In another terminal:

cd backend
celery -A app.workers.celery_app.celery_app beat --loglevel=info


⸻

Frontend local run

When frontend scaffolding is ready, run from project root:

npm install
npm run dev

Or directly in frontend:

cd frontend
npm install
npm run dev

Expected local frontend URL:

http://localhost:3000


⸻

Health checks

Backend health endpoint:

GET http://localhost:8000/api/v1/health

Readiness endpoint:

GET http://localhost:8000/api/v1/health/ready

Expected health response pattern:

{
  "data": {
    "status": "ok"
  }
}


⸻

Database migrations

Create a migration

From backend/:

alembic revision --autogenerate -m "init"

Apply migrations

alembic upgrade head

Roll back one revision

alembic downgrade -1


⸻

Running tests

From project root:

pytest

Or from backend:

cd backend
pytest

For a specific file:

pytest backend/tests/unit/test_load_service.py


⸻

Useful make targets

From project root:

Start stack:

make up

Stop stack:

make down

Run API:

make api

Run worker:

make worker

Run beat:

make beat

Run tests:

make test


⸻

Local storage

Sandbox storage path:

data/sandbox/uploaded-docs/

Additional local folders:

data/sandbox/extracted-results/
data/sandbox/test-results/

Use these for:
	•	document upload testing
	•	extraction output snapshots
	•	experiment files
	•	debugging artifacts

⸻

Suggested daily development flow

Backend-focused day
	1.	Activate virtual environment
	2.	Start Postgres and Redis with Docker
	3.	Run API locally
	4.	Run worker locally if needed
	5.	Run tests before commit

Full-stack day
	1.	docker compose up -d for infra
	2.	run backend
	3.	run frontend
	4.	verify /api/v1/health
	5.	verify main UI pages load

⸻

Common troubleshooting

Port 8000 already in use

Find the process and stop it, or run on another port.

Windows:

netstat -ano | findstr :8000

macOS/Linux:

lsof -i :8000


⸻

Port 3000 already in use

Check frontend conflicts or another Next.js process.

⸻

Database connection errors

Check:
	•	Postgres container is running
	•	DATABASE_URL is correct
	•	database name exists
	•	local firewall/VPN is not interfering

Docker check:

docker compose logs postgres


⸻

Redis connection errors

Check:
	•	Redis container is running
	•	REDIS_URL and CELERY_BROKER_URL are correct

Docker check:

docker compose logs redis


⸻

Alembic migration import failures

Usually caused by:
	•	wrong Python path
	•	missing model imports in backend/alembic/env.py
	•	environment variables not loaded

Run migrations from backend/, not project root, unless your shell setup already handles paths correctly.

⸻

Celery task not discovered

Check:
	•	task file exists under backend/app/workers/tasks/
	•	task is imported/discovered by celery_app.py
	•	worker restarted after task creation

⸻

Tests failing on SQLite vs Postgres differences

This is normal in early scaffolding.

If a model uses Postgres-specific types like JSONB or UUID, expect a cleanup pass later for SQLite-friendly test compatibility or test-specific adaptations.

⸻

What is acceptable right now

At this stage, it is acceptable that:
	•	some services are placeholders
	•	OCR is mocked
	•	extraction is simplified
	•	notification delivery is simulated
	•	some docs and flows are architecture-first

The current goal is to stabilize the structure before replacing placeholders with real trucking paperwork and real uncle workflow samples.

⸻

Next milestones after local setup works

Once local development is stable, the next practical steps are:
	1.	collect real rate cons, BOLs, and invoices
	2.	test upload flow against real samples
	3.	refine extraction fields
	4.	refine validation rules
	5.	refine workflow transitions
	6.	validate billing model against actual back-office process

⸻

Summary

Local development is considered healthy when:
	•	API starts successfully
	•	health endpoint returns ok
	•	Postgres and Redis are reachable
	•	tests run
	•	worker starts
	•	sample load and document flows can be exercised

Next file:

```text
docs/runbooks/deployment.md