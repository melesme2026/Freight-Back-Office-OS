# PR-48 Penetration Review Readiness Checklist

This document is a preparation checklist for a future independent penetration review. It is not a completed penetration test and does not claim that the platform is free of vulnerabilities.

## Scope Areas

- **Authentication and RBAC**
  - Validate staff, owner/admin, driver, and external portal role boundaries.
  - Confirm login success, login failure, logout, password reset, invite acceptance, and MFA actions create safe audit events.
  - Verify optional TOTP MFA cannot be enabled without a valid code and is not forced on existing users by default.
- **Tenant isolation**
  - Attempt cross-organization reads/writes for loads, documents, billing, analytics, support, command-center, and accounting exports.
  - Verify audit logs always stay organization-scoped.
- **Upload security**
  - Test file-size, extension/MIME validation, duplicate handling, storage-key handling, and private cache controls.
  - Confirm no raw document bytes are written into audit metadata or logs.
- **Portal token security**
  - Test tampered, expired, wrong-load, wrong-customer, and wrong-organization portal tokens.
  - Validate portal views/downloads/uploads are audited without storing portal tokens.
  - Confirm portal abuse routes are rate-limited while normal broker/customer usage remains usable.
- **Stripe webhook security**
  - Validate signature verification and idempotency/replay handling.
  - Confirm webhook routes are excluded from naive in-app rate limiting so Stripe retries are not broken.
- **Rate limiting**
  - Exercise login, password reset, request-demo, portal, external uploads, billing checkout, and document upload limit policies.
  - Confirm structured 429 responses include retry metadata and do not leak sensitive internals.
- **Security headers/cache controls**
  - Confirm CSP, frame protection, content-type sniffing protection, referrer policy, permissions policy, and production HSTS.
  - Confirm private API/file responses remain `no-store`.
- **Sensitive data handling**
  - Search audit metadata for passwords, reset tokens, portal tokens, authorization headers, Stripe secrets, card data, and raw documents.

## Known Residual Risks for Future Review

- In-memory application rate limiting is a foundation; production should add CDN/WAF or Redis-backed distributed limits.
- MFA recovery codes and admin recovery workflow are documented future work, not included in PR-48.
- CSP currently allows limited inline/eval compatibility for the existing app; future frontend hardening should remove those allowances.
- SOC2 readiness documents are starter controls and policies only; a formal audit, evidence collection, and control owner workflow remain future work.
- Enterprise SSO/SAML, SCIM, device posture, and full GRC evidence automation are not implemented in this PR.
