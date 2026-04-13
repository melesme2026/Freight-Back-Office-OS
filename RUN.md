# Freight Back Office OS — Runtime Recovery Runbook (Windows PowerShell)

## 1) Open repo

```powershell
cd C:\Development\Freight-Back-Office-OS
```

## 2) Python environment + deps (repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

## 3) Frontend deps

```powershell
cd .\frontend
npm install
cd ..
```

## 4) Required `.env` (repo root)

Use these keys (adjust DB host/password only if your local setup differs):

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

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

NEXT_PUBLIC_STRIPE_STARTER_LINK=https://buy.stripe.com/fZu8wP1HIc6m48R0PA7Vm00
NEXT_PUBLIC_STRIPE_GROWTH_LINK=https://buy.stripe.com/fZu7sL1HI7Q6fRz7dY7Vm01
NEXT_PUBLIC_ENTERPRISE_CONTACT=mailto:mermerbrands@gmail.com
```

## 5) Reset DB schema + verify billing columns + seed local users

> Run from repo root. This is the canonical local reset path.

```powershell
python .\backend\scripts\reset_db_and_seed.py
```

This command now:
1. drops all tables,
2. recreates schema from current models,
3. validates `organizations` has: `billing_provider`, `billing_status`, `plan_code`, `stripe_customer_id`, `stripe_subscription_id`, `billing_notes`,
4. seeds baseline local data.

### Seeded login credentials

- Organization ID: `00000000-0000-0000-0000-000000000001`
- Staff admin: `admin@adwafreight.com` / `Admin123!`
- Staff reviewer: `reviewer@adwafreight.com` / `Reviewer123!`
- Driver: `john.doe@example.com` / `Driver123!`

## 6) Start backend

```powershell
cd .\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 7) Backend runtime checks

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/v1/health`

Expected:
- `/docs` loads Swagger UI
- `/health` returns `{ "status": "ok" }`
- `/api/v1/health` returns API envelope with health payload

## 8) Start frontend (new terminal)

```powershell
cd C:\Development\Freight-Back-Office-OS\frontend
npm run dev
```

Open: `http://localhost:3000`

## 9) End-to-end QA (ordered)

1. Landing page:
   - Staff Login, Driver Login, Request Demo, View Pricing CTAs visible.
2. Pricing page (`/pricing`):
   - back-to-landing button visible,
   - Starter opens `https://buy.stripe.com/fZu8wP1HIc6m48R0PA7Vm00`,
   - Growth opens `https://buy.stripe.com/fZu7sL1HI7Q6fRz7dY7Vm01`,
   - Enterprise Contact Sales opens `mailto:mermerbrands@gmail.com`.
3. Request Demo page (`/request-demo`):
   - clear contact instructions,
   - working email CTA,
   - links back to landing/pricing.
4. Staff login (`/login`):
   - sign in with seeded admin,
   - verify dashboard pages load (`/dashboard`, `/dashboard/loads`, `/dashboard/documents`, `/dashboard/notifications`, `/dashboard/billing`).
5. Driver login (`/driver-login`):
   - sign in with seeded driver,
   - verify driver portal routes load (`/driver-portal`, `/driver-portal/uploads`, `/driver-portal/loads`).
6. Core ops:
   - staff upload from load detail succeeds,
   - driver upload succeeds,
   - load status update succeeds,
   - invoice generation succeeds,
   - notifications reflect upload and status events,
   - billing page renders and manual status override saves.

## 10) Intentionally unavailable (V1 known limits)

- Document detail: **Reprocess**
- Document detail: **Link to Load**
- Billing plans: **New Plan**
