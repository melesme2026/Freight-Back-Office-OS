# Freight Back Office OS — Run Guide

## Repo Location

```powershell
C:\Development\Freight-Back-Office-OS
```

---

## 1) Open the Project

```powershell
cd C:\Development\Freight-Back-Office-OS
```

---

## 2) Create Virtual Environment (first time only)

```powershell
python -m venv .venv
```

---

## 3) Activate Virtual Environment

### PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### CMD

```cmd
.venv\Scripts\activate.bat
```

---

## 4) Upgrade pip

```powershell
python -m pip install --upgrade pip
```

---

## 5) Install Project Dependencies

Install from the **repo root**, not from `backend`.

```powershell
pip install -e .[dev]
```

---

## 6) Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## 7) Environment File

Create or update `.env` in the repo root.

Example:

```env
APP_NAME=Freight Back Office OS API
APP_VERSION=0.1.0
ENVIRONMENT=local
DEBUG=true

SECRET_KEY=change-me-in-local-dev-only
JWT_EXPIRE_MINUTES=60

DATABASE_URL_OVERRIDE=postgresql+psycopg://postgres:postgres@localhost:5432/freight_back_office_os
REDIS_URL_OVERRIDE=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

CORS_ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]

STORAGE_LOCAL_ROOT=data/sandbox/uploaded-docs

LOG_LEVEL=INFO
LOG_JSON=true

AI_ENABLED=false
WHATSAPP_ENABLED=false
EMAIL_ENABLED=false
BILLING_ENABLED=false
```

## Important

* `CORS_ALLOWED_ORIGINS` must be a valid JSON array
* run backend commands from the `backend` folder for the current app import path
* use repo-root `.env`

---

## 8) Start Backend

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected success:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process ...
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 9) Backend Verification

Open these in browser:

```text
http://127.0.0.1:8000/api/v1/docs
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/api/v1/health/ready
```

### What to check

* `/api/v1/docs` opens successfully
* `/api/v1/health` returns basic service JSON
* `/api/v1/health/ready` returns readiness JSON
* no startup traceback in terminal

---

## 10) If Backend Fails

Use this workflow:

1. start backend
2. read the exact traceback
3. fix one blocker at a time
4. rerun the same command

Always copy the **full exact error**.

---

## 11) Common Backend Recovery Commands

### Reinstall dependencies

```powershell
pip install -e .[dev]
```

### Check installed package

```powershell
pip show python-jose
pip show fastapi
pip show uvicorn
```

### Clean pyc cache if needed

```powershell
Get-ChildItem -Path . -Recurse -Include __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Include *.pyc | Remove-Item -Force
```

---

## 12) Database Notes

Current local development is typically configured for Postgres via:

```env
DATABASE_URL_OVERRIDE=postgresql+psycopg://postgres:postgres@localhost:5432/freight_back_office_os
```

If you switch database strategy later, update `DATABASE_URL_OVERRIDE` accordingly.

---

## 13) Redis Notes

If Redis is required locally, make sure it is running and aligned to:

```env
REDIS_URL_OVERRIDE=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

---

## 14) Start Frontend

Run frontend after backend is stable.

```powershell
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## 15) Optional Docker Startup

From repo root:

```powershell
docker compose up -d
```

This starts the local stack defined in `docker-compose.yml`.

---

## 16) Recommended Daily Startup Flow

### Backend

```powershell
cd C:\Development\Freight-Back-Office-OS
.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

```text
http://127.0.0.1:8000/api/v1/docs
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/api/v1/health/ready
```

### Frontend

Open a second terminal:

```powershell
cd C:\Development\Freight-Back-Office-OS\frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## 17) Current Known Good State

Backend startup is successful when terminal shows:

```text
INFO:     Started server process ...
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

That means the current backend startup path is healthy.

---

## 18) Troubleshooting Rule

Do not redesign architecture during run phase.

Focus order:

1. backend startup
2. docs
3. health endpoints
4. ready endpoint
5. core routes
6. frontend
7. UI modernization