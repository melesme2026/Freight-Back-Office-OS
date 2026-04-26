# PR16 Launch Checklist

## 1. Pre-deploy checklist
- Confirm branch is up to date with `main`.
- Confirm backups/snapshots exist for production database.
- Confirm no demo seed mode is enabled in production (`SEED_MODE=minimal`).
- Confirm `alembic` head matches deployed revision.

## 2. Required environment variables
- `APP_ENV` (`production` on Render).
- `DATABASE_URL_OVERRIDE` (required for production).
- `SECRET_KEY` and JWT settings (`JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`).
- `CORS_ALLOWED_ORIGINS` (comma-separated).
- `WEB_APP_BASE_URL` (frontend public URL).
- `FRONTEND_API_URL` (frontend -> backend base URL).
- `EMAIL_SENDING_ENABLED` (`false` unless SMTP fully configured).
- SMTP vars when email sending is enabled: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM_ADDRESS`.
- Storage vars: `STORAGE_PROVIDER`, `STORAGE_LOCAL_ROOT` (if local) or bucket credentials for remote storage.
- `MAX_UPLOAD_FILE_SIZE_MB`.
- `PUBLIC_BACKEND_URL` (if used for public callbacks/docs links).

## 3. Docker/local smoke commands
```bash
git pull
docker-compose down
docker-compose up -d --build
docker-compose ps
docker-compose logs -f api
```

## 4. Alembic migration commands
```bash
cd backend
alembic upgrade head
```

## 5. Render deployment checklist
1. Verify all required env vars are set in Render dashboard.
2. Deploy latest `main`.
3. Confirm deploy logs show successful startup and DB connectivity.
4. Validate `/api/v1/health` and `/api/v1/health/readiness`.

## 6. Post-deploy smoke test checklist
```bash
pytest backend/tests/integration/test_launch_smoke_flow.py -q
npm --prefix frontend run typecheck
npm --prefix frontend run lint
```
- Owner/Admin: create load, upload docs, generate invoice, create packet, download zip, mark sent, record partial + paid reconciliation, generate follow-ups, check money dashboard.
- Driver: only assigned load visible, can upload POD/BOL, blocked from money dashboard/payment/submission packet APIs.

## 7. Rollback plan
1. Re-deploy previous stable image/version in Render.
2. If required, restore DB from snapshot taken pre-deploy.
3. Re-run health/readiness checks.
4. Run smoke tests against rollback version.

## 8. First pilot user onboarding
1. Create organization and owner/admin account.
2. Complete carrier profile before invoice/packet workflows.
3. Add brokers/customers/drivers with real tenant data (no demo seed in prod).
4. Walk through one real load end-to-end.

## 9. Known limitations
- Local readiness does not validate external third-party provider reachability beyond config sanity.
- Packet email sending is blocked when `EMAIL_SENDING_ENABLED=false`.
- Minimal seed mode intentionally creates no business records.

## 10. Support / troubleshooting
- Missing carrier profile: complete `/dashboard/settings/carrier-profile` before invoice generation.
- Email disabled: expected when `EMAIL_SENDING_ENABLED=false`.
- Missing SMTP config: startup validation fails if sending enabled without required SMTP vars.
- Missing packet docs: upload rate confirmation/BOL/POD/invoice before packet creation.
- Migration not applied: run `alembic upgrade head` and restart services.
