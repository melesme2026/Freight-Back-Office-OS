# Playwright E2E Launch Suite

## PR-L3 browser readiness root cause
The E2E launch gate was blocked by environment and runbook readiness, not by a production-data dependency: `npm --prefix frontend run test:e2e -- --list` could enumerate specs, but Chromium execution could not start in Codex when the Playwright Chromium download endpoint returned `403 Forbidden`. PR-L3 makes browser installation explicit, adds deterministic local/CI commands, hardens mock data, and documents coverage and remaining environment limits.

## Prerequisites
1. Install Node dependencies from the repository root:
   - `npm ci`
2. Install the Playwright Chromium browser from the frontend workspace:
   - `npm --prefix frontend run e2e:install`
   - Equivalent direct command: `npx --prefix frontend playwright install chromium`
   - Linux CI can use `npx --prefix frontend playwright install --with-deps chromium` when OS browser dependencies are not preinstalled.
3. No Stripe, SMTP, Render, or production data is required. The suite uses deterministic frontend route mocks for API calls under `/api/v1/**`.

## Required launch-gate commands
- Enumerate specs without launching a browser:
  - `npm --prefix frontend run e2e:list`
  - Equivalent: `npm --prefix frontend run test:e2e -- --list`
- Install the desktop/mobile Chromium browser binary:
  - `npm --prefix frontend run e2e:install`
  - Direct acceptance command: `npx --prefix frontend playwright install chromium`
- Run desktop Chromium:
  - `npm --prefix frontend run e2e:chromium`
  - Equivalent: `npm --prefix frontend run test:e2e -- --project=chromium`
- Run mobile Chrome emulation:
  - `npm --prefix frontend run e2e:mobile`
  - Equivalent: `npm --prefix frontend run test:e2e -- --project=mobile-chrome`
- Headed local debugging:
  - `npm --prefix frontend run e2e:headed`
- Open HTML report:
  - `npm --prefix frontend run test:e2e:report`

## Playwright configuration
- Config file: `frontend/playwright.config.ts`
- Test directory: `frontend/e2e/specs`
- Projects:
  - `chromium` uses Playwright `Desktop Chrome`.
  - `mobile-chrome` uses Playwright `Pixel 7`.
- `PLAYWRIGHT_BASE_URL` is configurable and defaults to `http://127.0.0.1:3000`.
- `PLAYWRIGHT_WEB_SERVER_COMMAND` can override the default web server command. The default is `npm run build && npm run start` from `frontend/`.
- The web server sets safe test defaults for public API prefix, billing mode, and public signup. Tests still mock API requests and do not require live backend services.
- CI uses retries, `forbidOnly`, and two workers for repeatability.

## Test data and mocks
- Deterministic fixtures live in `frontend/e2e/fixtures/test-data.ts`.
- Mock API handlers live in `frontend/e2e/support/mock-api.ts`.
- Mocked flows include auth, RBAC redirects, owner dashboard routes, driver portal routes, uploads, billing pilot state, analytics, command center, accounting exports, document inventory, and broker/customer portal token states.
- Upload fixtures are safe test files in `frontend/e2e/fixtures/files/`.

## Coverage matrix
| Area | PR-L3 readiness status |
| --- | --- |
| Public homepage renders | Covered by `public-marketing.spec.ts`. |
| Pricing renders | Covered by `public-marketing.spec.ts` and `billing-and-negative.spec.ts`. |
| Request-demo validation | Covered by `public-marketing.spec.ts` with browser validity checks. |
| Request-demo success state | Covered by `public-marketing.spec.ts` with a mocked 201 response. |
| Owner login | Covered by `auth-multi-org.spec.ts` and owner workflow specs. |
| Owner dashboard access | Covered by `owner-route-smoke.spec.ts`. |
| Carrier profile route | Covered by `owner-route-smoke.spec.ts` and `owner-admin-workflow.spec.ts`. |
| Customer, broker, and load route smoke | Covered by `owner-admin-workflow.spec.ts`; load list/detail covered by route smoke/workflow. |
| Document upload UI route smoke | Covered by `owner-route-smoke.spec.ts` for document inventory and `owner-admin-workflow.spec.ts` for upload controls. |
| Invoice/packet route smoke | Covered by `owner-admin-workflow.spec.ts` and invoice route smoke. |
| Analytics route smoke | Covered by `owner-route-smoke.spec.ts` with deterministic analytics mocks. |
| Command center route smoke | Covered by `owner-route-smoke.spec.ts` with deterministic command center mocks. |
| Accounting/export route smoke | Covered by `owner-route-smoke.spec.ts` with deterministic accounting mocks. |
| Owner logout cleanup | Covered by `portal-security.spec.ts`. |
| Staff login/permitted dashboard access | Covered by `auth-multi-org.spec.ts` using the staff/owner dashboard entry point. |
| Owner-only restriction | Covered by `portal-security.spec.ts` driver dashboard denial. |
| Driver login and portal redirect | Covered by `auth-multi-org.spec.ts` and `driver-portal-rbac.spec.ts`. |
| Driver assigned loads visible | Covered by `driver-portal-rbac.spec.ts`. |
| Driver dashboard/admin route denial | Covered by `driver-portal-rbac.spec.ts` and `portal-security.spec.ts`. |
| Driver upload UI smoke | Covered by `driver-portal-rbac.spec.ts` and `mobile-smoke.spec.ts`. |
| Driver mobile viewport smoke | Covered by `mobile-smoke.spec.ts` under the `mobile-chrome` project. |
| Driver logout cleanup | Covered by `portal-security.spec.ts`. |
| Portal invalid token state | Covered by `portal-security.spec.ts`. |
| Portal expired/unauthorized state | Covered by `portal-security.spec.ts`. |
| Portal authorized state | Covered by `portal-security.spec.ts`. |
| Portal upload/download controls smoke | Covered by `portal-security.spec.ts`. |
| Unauthenticated protected route redirect | Covered by `portal-security.spec.ts`. |
| Logout clears access | Covered by `portal-security.spec.ts`. |
| Browser-back-after-logout behavior | Covered by `portal-security.spec.ts`. |
| PWA manifest reachable | Covered by `mobile-smoke.spec.ts`. |
| Service worker file reachable | Not applicable unless a service worker file is added; current PWA shell coverage is manifest-first. |
| Mobile navigation/viewport overflow | Covered by `mobile-smoke.spec.ts` core route overflow checks. |

## CI behavior
The GitHub Actions workflow `.github/workflows/playwright-e2e.yml` runs:
1. `npm ci`
2. `npm --prefix frontend run e2e:install`
3. `npm --prefix frontend run e2e:list`
4. `npm --prefix frontend run e2e:chromium`
5. Uploads `frontend/playwright-report` and `frontend/test-results` on every run.

## Artifacts and failure triage
On failure Playwright captures:
- screenshots: `only-on-failure`
- videos: `retain-on-failure`
- traces: `retain-on-failure`
- HTML report: `frontend/playwright-report`
- raw results: `frontend/test-results`

Use `npm --prefix frontend run test:e2e:report` and the trace viewer to inspect failed steps, network calls, console output, screenshots, and video.

## Known limitations
- Codex may be unable to install Chromium if the Playwright CDN returns `403 Forbidden`; use `npm --prefix frontend run e2e:install` locally/CI where the CDN is reachable.
- The suite intentionally validates launch-critical browser flows using deterministic mocks rather than live Stripe, SMTP, Render, or production tenant data.
- Service worker reachability is documented as not applicable until a service worker asset exists.
