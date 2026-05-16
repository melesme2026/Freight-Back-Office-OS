# Mobile Upload UX Audit Follow-Ups

Captured during the mobile document upload UX audit for the load detail page on 2026-05-16. These are intentionally tracked for later launch-readiness PRs and are not addressed by the mobile upload UX fix.

## Production configuration and domain follow-ups

- Generated driver activation URLs currently use `fbos-nginx.onrender.com` instead of `https://app.adwafreight.com`.
- Render health endpoint reports `environment=staging` instead of production.
- Set `WEB_APP_BASE_URL=https://app.adwafreight.com` for production.
- Ensure `CORS_ALLOWED_ORIGINS` includes `https://app.adwafreight.com`.
- Define the `www.adwafreight.com` / `adwafreight.com` redirect plan.

## Product and brand follow-ups

- Replace the temporary “FB” mark with the eventual real logo.
- Add a future Driver Readiness Status / compliance workflow.
