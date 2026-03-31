# Security Model

## Purpose

This document defines the security model for Freight Back Office OS.

It covers:

* authentication
* authorization direction
* tenant isolation
* API security
* webhook security
* file security
* secrets handling
* V1 security priorities

---

## Why security matters

This platform handles sensitive operational and financial data such as:

* driver contact information
* customer account information
* load and broker data
* billing records
* invoice and payment information
* uploaded freight documents

Even in V1, security must be treated as a core design concern.

The goal is not perfect enterprise compliance on day one. The goal is to build a secure foundation that can be hardened over time.

---

## Security principles

The platform follows these principles:

* least privilege
* explicit access boundaries
* secure defaults
* tenant-aware data handling
* no hardcoded secrets
* auditability of sensitive actions
* progressive hardening over time

---

## Main security layers

The security model includes:

1. authentication
2. authorization
3. tenant isolation
4. secret management
5. webhook and integration security
6. document and file protection
7. auditability
8. operational safeguards

---

## 1. Authentication

Authentication determines who or what is calling the system.

### Current foundation

The project includes:

* `auth_service.py`
* `token_service.py`
* password hashing
* bearer token handling
* staff user auth routes
* API client model foundation

### Staff authentication

Staff users authenticate using:

* email
* password

Passwords must never be stored in plain text.

Passwords should be stored as secure password hashes.

### Token-based access

Authenticated sessions should use bearer tokens.

Typical pattern:

```text
Authorization: Bearer <token>
```

The token should identify:

* user ID
* organization ID
* role
* expiration

### API client authentication

The `ApiClient` model exists for machine-to-machine access.

This is useful for:

* external integrations
* internal automation
* system webhooks
* partner APIs

V1 may keep this simple, but the model should support API-key or token-based access later.

---

## 2. Authorization

Authorization determines what an authenticated actor is allowed to do.

### V1 status

V1 includes the structural foundation for roles, but full fine-grained RBAC is not expected to be complete yet.

That is acceptable.

### Role foundation

The system includes a role enum and staff user role field.

Examples of future roles:

* `admin`
* `ops_agent`
* `reviewer`
* `finance_user`
* `support_user`
* `read_only_user`

### Authorization direction

Eventually, authorization should control:

* who can view or update loads
* who can resolve validation issues
* who can manage billing records
* who can modify service plans
* who can manage staff users
* who can access support and audit data

---

## 3. Tenant isolation

Tenant isolation is one of the most important security boundaries in the system.

### Core rule

An organization must not be able to access another organization's data.

This applies to:

* customer accounts
* drivers
* brokers
* loads
* documents
* invoices
* payments
* support tickets
* audit logs

### Implementation pattern

Most major records belong to an `organization_id`.

All repository and service logic should respect this boundary.

### V1 requirement

Even if the system is initially used by one business, the code should still preserve tenant-aware design because the platform is intended to grow into multi-customer SaaS.

---

## 4. Secrets handling

Secrets must never be hardcoded into the codebase.

Examples of secrets:

* JWT secret keys
* database credentials
* Redis credentials
* payment provider keys
* webhook signing secrets
* API client secrets

### V1 rule

Secrets should live in:

* `.env`
* environment variables
* future secret manager integration

Never commit live secrets to source control.

---

## 5. Password security

Passwords must be:

* hashed
* salted
* never logged
* never returned in API responses

The backend should only store a password hash, not the original password.

---

## 6. Webhook security

Webhook endpoints are external entry points and must be treated as sensitive.

Current webhook endpoints include:

* WhatsApp
* email
* payment

### V1 acceptable baseline

In V1, basic payload validation and controlled routing are acceptable as a starting point.

### Future hardening

Webhook security should evolve to include:

* signature verification
* replay protection
* source validation
* rate limiting
* idempotency tracking

---

## 7. File and document security

Uploaded documents are sensitive.

Examples:

* rate confirmations
* bills of lading
* invoices
* proofs of delivery

These may contain:

* addresses
* broker information
* rates
* customer details
* signatures

### Required controls

At minimum, the system should:

* restrict allowed file types
* sanitize file names
* store files in controlled locations
* avoid exposing raw filesystem paths directly
* avoid public access by default

### Future controls

Later enhancements should include:

* signed URL access
* access-controlled download endpoints
* malware scanning
* file size restrictions
* encryption at rest where applicable

---

## 8. API security

The API is the operational control plane of the system.

Security expectations include:

* input validation
* structured exception handling
* no sensitive data leakage in errors
* role-based enforcement later
* organization-aware access patterns
* secure authentication flows

### Validation

Pydantic schemas and explicit request validation help prevent malformed input.

### Error handling

Errors should be informative enough for diagnosis, but should not leak secrets or internal implementation details.

---

## 9. Auditability of sensitive actions

Sensitive actions should be auditable.

Examples:

* login activity
* role or status changes
* billing updates
* payment changes
* validation issue resolution
* customer account edits

This allows investigation of:

* who changed data
* when it changed
* what changed

---

## 10. Operational security

Security is not only code-level.

Operational security includes:

* protecting environment variables
* limiting infrastructure access
* restricting database access
* controlling deployment credentials
* rotating secrets
* using HTTPS in non-local environments

---

## 11. Local development security

For local development:

* test credentials are acceptable
* fake secrets are acceptable
* debug mode is acceptable

But even locally:

* do not commit secrets
* do not use production keys
* do not expose local services publicly without intent

---

## 12. V1 realistic security priorities

The following are the most important security goals for V1.

### Must have

* password hashing
* basic token auth foundation
* tenant-aware model design
* no hardcoded secrets
* input validation
* safe file handling baseline
* structured error handling
* audit foundation

### Can come later

* full RBAC
* advanced webhook signature validation
* centralized secrets manager
* advanced rate limiting
* full production IAM model
* deep compliance posture

---

## 13. Threat examples

The system should be designed with common risks in mind.

### Unauthorized data access

Risk:

* one user accesses another organization's data

Mitigation:

* enforce organization boundaries

### Secret leakage

Risk:

* credentials committed to the repository or exposed in logs

Mitigation:

* environment variables
* secret hygiene
* log discipline

### Malicious upload

Risk:

* dangerous or oversized files uploaded

Mitigation:

* file validation
* controlled storage
* future scanning

### Forged webhook

Risk:

* attacker posts fake payment or ingestion payloads

Mitigation:

* future signature verification
* idempotency
* source validation

### Excessive privilege

Risk:

* too many users can modify billing or sensitive operations

Mitigation:

* future role-based authorization
* audit logging

---

## 14. Future security roadmap

After V1, security should evolve toward:

* full RBAC
* stronger JWT or session policy
* refresh token strategy
* API key management for integrations
* webhook signature verification
* file malware scanning
* download authorization
* secret manager integration
* security headers and CSP
* rate limiting
* SSO or enterprise authentication options

---

## 15. Security design summary

### Identity

* staff user authentication
* API client foundation

### Access

* tenant-aware design
* role-aware future direction

### Data protection

* safe secrets handling
* password hashing
* controlled document access

### Accountability

* audit logs
* workflow event history

### Hardening path

* V1 secure foundation
* post-V1 stronger enforcement

---

## Summary

The security model for Freight Back Office OS is designed to be practical for V1 and strong enough to evolve into a serious multi-tenant SaaS platform.

The immediate goal is to ensure:

* authenticated access
* safe secret handling
* tenant-aware structure
* secure file and API foundations
* auditability of important actions

That gives the system a solid baseline without overcomplicating the first release.
