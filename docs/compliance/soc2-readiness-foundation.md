# SOC2 Readiness Foundation — Starter Control Mapping

This is a SOC2 readiness foundation and preparation structure. It is not a SOC2 certification, audit report, or compliance claim.

## Starter Controls Map

| Area | Starter control intent | PR-48 foundation |
| --- | --- | --- |
| Access control | Users authenticate with scoped roles and least-privilege access. | Existing RBAC remains unchanged; optional TOTP MFA foundation and auth audit events were added. |
| Logical tenant isolation | Customer data is scoped by organization. | Audit and penetration-review checklist require cross-tenant validation for sensitive modules. |
| Change accountability | Sensitive administrative and security actions are traceable. | Audit sanitization and auth/MFA/password/invite audit coverage were strengthened. |
| Abuse prevention | Public and sensitive endpoints resist high-volume abuse. | In-app configurable rate limits protect login, password reset, request-demo, portal, uploads, and billing checkout. |
| Secure communications | Browser responses reduce common web attack surface. | Security headers include CSP, frame protection, MIME sniffing protection, referrer policy, permissions policy, and production HSTS. |
| Sensitive data handling | Secrets, tokens, payment data, and documents are not stored in logs. | Audit metadata recursively redacts sensitive keys and truncates large strings. |
| Incident readiness | Operators have a baseline response process. | Incident response skeleton below identifies severity, triage, communication, containment, and postmortem steps. |
| Vendor/payment handling | Third-party integrations are reviewed for secure operations. | Stripe webhook security and retry-safe rate-limit exclusion are documented for review. |

## Security Policy Skeleton

- Maintain least-privilege access for staff and operational roles.
- Require unique user accounts; prohibit shared administrative credentials.
- Offer optional MFA for staff accounts and plan future administrative MFA policy controls.
- Log sensitive actions with safe request context where available.
- Never log passwords, auth tokens, portal tokens, reset tokens, Stripe secrets, card data, or raw private documents.
- Review security-relevant changes before production deployment.

## Access Control Notes

- Owner/admin roles manage staff access; lower-privileged roles are restricted by existing RBAC.
- Driver and external portal flows must remain scoped to their assigned driver/load/customer context.
- MFA is opt-in in PR-48 to avoid locking out existing users.
- Future work should define tenant-level MFA enforcement and break-glass procedures.

## Incident Response Skeleton

1. **Identify:** classify alert/source, affected tenant(s), data classes, and suspected entry point.
2. **Triage severity:** critical for active compromise, credential theft, payment data exposure, or cross-tenant access.
3. **Contain:** disable compromised accounts/tokens, rotate secrets, pause affected integrations if needed.
4. **Investigate:** preserve audit logs, request IDs, deployment history, and relevant provider events.
5. **Communicate:** notify internal owner, customer contacts, vendors, and legal/privacy stakeholders as appropriate.
6. **Recover:** patch, deploy, validate, restore service, and monitor for recurrence.
7. **Postmortem:** document root cause, timeline, customer impact, control gaps, and corrective actions.

## Audit Log Coverage Notes

- Required fields: organization, actor type/id where available, action, entity type/id, timestamp, safe metadata, and request context when available.
- PR-48 adds auth and MFA audit coverage and improves sanitization.
- Existing operational audit events should continue to be expanded as new sensitive workflows are added.

## Data Retention and Security Notes

- Define retention periods for audit logs, uploaded documents, extracted data, support records, and billing records before SOC2 audit readiness.
- Ensure private documents and billing-related records retain no-store cache controls.
- Keep customer data export and deletion procedures documented before enterprise onboarding.

## Vendor/Security Notes

- Stripe is the primary payment provider; webhook signature verification and retry behavior must be part of recurring reviews.
- Email delivery, storage, infrastructure, monitoring, and AI vendors should receive security review records before formal SOC2 audit work.
- Maintain a vendor inventory with data categories, subprocessors, regions, and contract/security documentation.
