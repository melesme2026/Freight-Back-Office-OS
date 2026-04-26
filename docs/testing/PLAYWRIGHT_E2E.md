# Playwright E2E Launch Suite

## Purpose
This browser suite complements backend smoke tests by validating real user routing, UI wiring, RBAC visibility, upload behavior, and launch-critical feedback states.

## Prerequisites
1. Install frontend dependencies:
   - `npm --prefix frontend install`
2. Install Playwright browsers:
   - `npm --prefix frontend exec playwright install --with-deps chromium`
3. Backend smoke prerequisite:
   - `pytest backend/tests/integration/test_launch_smoke_flow.py -q`

## Run Commands
- Headless CI/local run:
  - `npm --prefix frontend run test:e2e`
- Headed interactive run:
  - `npm --prefix frontend run test:e2e:headed`
- Debug mode:
  - `npm --prefix frontend run test:e2e:debug`
- Open HTML report:
  - `npm --prefix frontend run test:e2e:report`

## Environment Variables
- `PLAYWRIGHT_BASE_URL` (optional, default `http://127.0.0.1:3000`)
- `CI=true` enables retries configured in `playwright.config.ts`.
- Optional frontend envs can still be used (`NEXT_PUBLIC_PUBLIC_SIGNUP_ENABLED`, Stripe links), but test suite provides mock API responses.

## Docker / local stack sequence
1. Start local stack (if running full integration stack) via project Docker runbook.
2. Run backend launch smoke.
3. Run frontend Playwright suite.

## Artifacts and failure triage
On failure Playwright captures:
- screenshots (`only-on-failure`)
- video (`retain-on-failure`)
- traces (`retain-on-failure`)
- HTML report (`frontend/playwright-report`)

Use trace viewer from the HTML report to inspect failed steps, network activity, and console/page errors.

## Known limitations
- The suite uses deterministic mock API handlers for launch gating and RBAC flows, so it avoids requiring real Stripe, SMTP, or customer production data.
- It is focused on launch smoke quality, not exhaustive UI regression or full accessibility audit.
- File upload fixtures are test-safe sample files only.

## Coverage summary
- Public marketing routes and CTAs
- Signup gating and validation behavior
- Owner/admin core launch workflow (login → load detail → docs/invoice/packet/payment)
- Driver portal flow + RBAC blocking
- Billing safety copy and disabled-checkout behavior
- Negative cases (invalid login, invalid upload type)
- Mobile viewport smoke
