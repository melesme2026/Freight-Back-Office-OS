# Load Detail Production Meltdown Fix

## Root cause summary

The load detail screen behaved like a parallel monolith: it loaded the core load record at the same time as documents, packet audit, submission packets, payment reconciliation, review context, and staff users. On slow mobile Safari sessions, those concurrent requests timed out, were retried or refreshed, and created 499 storms that saturated backend workers. The heaviest backend paths also hydrated related document, validation, workflow, and staff relationships that the initial interactive view did not need.

## Architecture change

The page now performs staged hydration:

1. Fetch `/loads/:id` first as the hard-isolated core load detail response.
2. Defer documents, packet audit, submission packets, carrier profile, payment reconciliation, follow-ups, review queue context, and staff users behind timed panel hydration.
3. Abort pending hydration requests and scheduled panel fetches when the route changes or the component unmounts.
4. Let each panel fail independently while keeping the core page interactive.

## Endpoint timing table and budgets

| Endpoint | Before | After target / guard | Change |
| --- | --- | --- | --- |
| `GET /loads/:id` | Core response competed with secondary panels and could be delayed by worker saturation. | CI guard: `<1000ms`; production target: `<300ms` for isolated core data. | Core route uses `core_detail=True` and does not hydrate documents, validation issues, packet aggregation, or workflow events. |
| `GET /loads/:id/documents` | Returned fully hydrated document records, including related load/user/field/validation data. | CI guard: `<500ms`. | Returns lightweight rows only: `id`, `filename`, `type`, `uploaded_at`, and `status`. |
| `POST /documents/upload` | Upload response serialized the full document model and could be coupled to downstream analysis work. | CI guard: `<800ms`. | Response now returns the same lightweight document row while extraction/validation remains queued as background work. |
| Secondary panels | Requested in an initial burst. | Staggered hydration; mobile Safari uses larger gaps. | Documents, packet audit, submission packets, payment reconciliation, review context, and staff users are deferred. |

## ORM/query improvements

- Load core detail avoids `Load.documents`, `Load.validation_issues`, and `Load.workflow_events` hydration.
- Load documents endpoint uses `include_related=False`, preventing ORM hydration of `LoadDocument.load`, `uploaded_by_staff_user`, `extracted_fields`, and `validation_issues`.
- Staff user list uses `include_related=False`, avoiding broad team relationship loading for the load-detail assignee dropdown.
- Upload response serialization uses the lightweight document shape instead of touching relationship-backed serializer fields.

## Production proof hooks

Every API request now emits and returns timing diagnostics:

- `Server-Timing: db;dur=..., serialize;dur=..., total;dur=...`
- `X-Process-Time-Ms`
- `X-Query-Count`

Logs include endpoint path, method, status, total duration, DB query duration, serialization duration, query count, request ID, and organization ID. Query-heavy requests (`>=20` SQL statements), slow requests, and 5xx requests are warning-level so N+1 explosions show up in production logs.
