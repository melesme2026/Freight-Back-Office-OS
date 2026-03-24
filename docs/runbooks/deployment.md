# Deployment Runbook

## Purpose

This runbook explains how to deploy Freight Back Office OS across environments:

- local
- staging
- production (future)

It covers:

- deployment architecture
- environment configuration
- build and release flow
- container deployment
- database migrations
- verification steps
- rollback strategy

---

## Deployment architecture

### Core components

The system consists of:

- API (FastAPI)
- Worker (Celery)
- Scheduler (Celery Beat)
- Database (PostgreSQL)
- Cache/Queue (Redis)
- Frontend (Next.js)
- Reverse proxy (Nginx)

---

### Logical architecture

```text
[Frontend (Next.js)]
        ↓
[Nginx / API Gateway]
        ↓
[FastAPI Backend]
        ↓
[PostgreSQL]   [Redis]
                  ↓
             [Celery Worker]
                  ↓
             [Background Tasks]


⸻

Environments

Local
	•	Docker Compose
	•	SQLite or local Postgres
	•	Redis local

Staging (recommended next step)
	•	Docker or VM-based
	•	Real Postgres + Redis
	•	Test integrations

Production (future)
	•	Kubernetes (preferred)
	•	Managed DB (RDS / Cloud SQL)
	•	Managed Redis
	•	CDN + HTTPS

⸻

Environment variables

All deployments require:

APP_ENV
DATABASE_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
REDIS_URL
SECRET_KEY
CORS_ALLOWED_ORIGINS
STORAGE_LOCAL_ROOT_PATH

Never hardcode secrets.

⸻

Build process

Backend

docker build -f infra/docker/api.Dockerfile -t freight-api .

Worker

docker build -f infra/docker/worker.Dockerfile -t freight-worker .

Frontend

docker build -f infra/docker/web.Dockerfile -t freight-web .


⸻

Local deployment (reference)

docker compose up -d


⸻

Staging deployment (VM-based example)

Step 1: Pull latest code

git pull origin main

Step 2: Build images

docker compose build

Step 3: Apply migrations

docker compose run api alembic upgrade head

Step 4: Start services

docker compose up -d


⸻

Kubernetes deployment (future-ready)

Located in:

infra/k8s/

Key manifests:
	•	api-deployment.yaml
	•	worker-deployment.yaml
	•	web-deployment.yaml
	•	redis.yaml
	•	postgres.yaml

Apply:

kubectl apply -f infra/k8s/


⸻

Database migrations (critical)

Always run before deploying new code:

alembic upgrade head

Failure to run migrations may break:
	•	API
	•	worker tasks
	•	billing logic

⸻

Health verification

After deployment:

API

GET /api/v1/health

Expected:

{
  "data": {
    "status": "ok"
  }
}


⸻

Worker

Check logs:

docker logs freight_back_office_worker


⸻

Database

Check connection manually or via logs.

⸻

Deployment checklist

Before deploy:
	•	tests pass
	•	migrations generated
	•	env variables set
	•	Docker builds succeed

After deploy:
	•	API healthy
	•	worker running
	•	migrations applied
	•	logs clean
	•	frontend reachable

⸻

Rollback strategy

If deployment fails:

Option 1: rollback code

git checkout <previous_commit>
docker compose up -d --build


⸻

Option 2: rollback DB (careful)

alembic downgrade -1

Use only if migration caused issue.

⸻

Logging

View logs:

docker compose logs -f

Focus:
	•	API errors
	•	worker failures
	•	DB connection issues

⸻

Common deployment issues

1. DB connection failure
	•	wrong DATABASE_URL
	•	DB not started
	•	network issue

⸻

2. Redis not reachable
	•	wrong REDIS_URL
	•	container not running

⸻

3. Worker not processing tasks
	•	queue misconfigured
	•	worker not running
	•	tasks not registered

⸻

4. Migration errors
	•	missing imports in env.py
	•	schema mismatch
	•	incompatible DB state

⸻

5. CORS issues
	•	wrong frontend URL in env
	•	missing origin in CORS_ALLOWED_ORIGINS

⸻

Security basics
	•	never commit .env
	•	use strong SECRET_KEY
	•	restrict DB access
	•	enable HTTPS in production
	•	rotate credentials periodically

⸻

Future improvements
	•	CI/CD pipeline (GitHub Actions)
	•	zero-downtime deployments
	•	blue/green or canary deploys
	•	automated DB backups
	•	monitoring (Prometheus, Grafana)
	•	alerting (Slack, email)

⸻

Summary

A successful deployment ensures:
	•	API is running
	•	workers are processing jobs
	•	database is migrated
	•	system is reachable
	•	logs are clean

This runbook is the baseline for safely deploying Freight Back Office OS.

---