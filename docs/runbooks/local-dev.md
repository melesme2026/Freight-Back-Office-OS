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

Freight-Back-Office-OS/

Key folders:

- backend/
- frontend/
- infra/
- docs/
- data/

---

## Prerequisites

Install the following first:

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git

Recommended:

- VS Code or IntelliJ
- Postman or Bruno
- pgAdmin or TablePlus

---

## Environment file

Create a local `.env` in the project root.

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

---

## Option 1: Docker-based local stack

Start:

```bash
docker compose up -d

Check:

docker compose ps

Logs:

docker compose logs -f api

Stop:

docker compose down


⸻

Option 2: Manual backend run

Create venv:

python -m venv .venv

Activate:

.venv\Scripts\Activate.ps1

Install:

pip install -e .

Run API:

cd backend
uvicorn app.main:app --reload

Worker:

celery -A app.workers.celery_app.celery_app worker --loglevel=info


⸻

Frontend

cd frontend
npm install
npm run dev


⸻

Health check

GET http://localhost:8000/api/v1/health


⸻

Migrations

alembic upgrade head


⸻

Tests

pytest


⸻

Local storage

data/sandbox/uploaded-docs/


⸻

Summary

Local setup is working when:
	•	API runs
	•	health endpoint works
	•	DB + Redis connect
	•	tests run

---
