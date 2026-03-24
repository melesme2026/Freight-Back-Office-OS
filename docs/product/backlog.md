# Product Backlog

## Purpose

This backlog captures all known and anticipated work for Freight Back Office OS.

It includes:

- features
- improvements
- technical debt
- future ideas

Items are grouped by priority and phase.

---

## Priority levels

- P0 → Critical (must have for V1 validation)
- P1 → High (needed soon after V1)
- P2 → Medium (important but not urgent)
- P3 → Low (future or nice-to-have)

---

## P0 — Critical (V1 validation)

These are required to make the system usable with real paperwork.

### Core workflow

- [ ] Upload real documents (rate con, BOL, invoice)
- [ ] Link documents to loads correctly
- [ ] Ensure load lifecycle works end-to-end
- [ ] Ensure workflow transitions are correct

---

### Extraction

- [ ] Identify real fields from actual documents
- [ ] Improve extraction_service based on real samples
- [ ] Handle missing/unclear fields gracefully

---

### Validation

- [ ] Ensure validation rules match real-world issues
- [ ] Add missing rules discovered during testing
- [ ] Ensure blocking vs non-blocking logic is correct

---

### Review flow

- [ ] Review queue shows real issues clearly
- [ ] Ability to correct extracted fields
- [ ] Ability to resolve validation issues

---

### Stability

- [ ] Fix any crashes during document processing
- [ ] Ensure worker tasks complete reliably
- [ ] Ensure no data loss

---

## P1 — High priority

These improve usability and reduce manual effort.

### Automation

- [ ] Auto-classify documents more accurately
- [ ] Auto-link documents to loads
- [ ] Improve load matching logic

---

### Notifications

- [ ] Notify driver when document missing
- [ ] Notify when load is ready
- [ ] Notify on validation issues

---

### Billing

- [ ] Improve invoice generation accuracy
- [ ] Ensure usage tracking is correct
- [ ] Improve payment handling

---

### UI (basic)

- [ ] Load list page
- [ ] Load detail page
- [ ] Review queue UI
- [ ] Document viewer

---

## P2 — Medium priority

These support scaling and better operations.

### Onboarding

- [ ] Improve onboarding checklist logic
- [ ] Add onboarding UI
- [ ] Track onboarding progress visually

---

### Reporting

- [ ] Basic dashboard metrics
- [ ] Load counts
- [ ] billing totals
- [ ] processing time

---

### Support

- [ ] Improve support ticket workflow
- [ ] Add better ticket filtering
- [ ] Link tickets more tightly to loads

---

### API improvements

- [ ] Add filtering and search
- [ ] Improve pagination
- [ ] Add better error messages

---

## P3 — Low priority / Future

These are long-term improvements.

### AI

- [ ] Improve extraction accuracy using real datasets
- [ ] Add anomaly detection improvements
- [ ] Suggest corrections automatically

---

### Billing advanced

- [ ] Discounts and coupons
- [ ] Tax calculation
- [ ] multi-currency support
- [ ] refund handling

---

### Platform

- [ ] multi-tenant isolation improvements
- [ ] role-based access control
- [ ] API rate limiting

---

### Integrations

- [ ] Stripe integration
- [ ] QuickBooks integration
- [ ] factoring systems

---

## Tech debt

- [ ] clean up placeholder services
- [ ] refactor duplicated logic
- [ ] improve logging consistency
- [ ] improve error handling
- [ ] improve test coverage

---

## Ideas / future exploration

- [ ] driver mobile experience
- [ ] AI assistant for support
- [ ] automatic load reconciliation
- [ ] predictive billing insights

---

## Backlog usage

This backlog should be:

- reviewed weekly
- updated after real workflow testing
- refined based on actual pain points

---

## Key rule

Do not blindly build from backlog.

Always prioritize based on:

1. real workflow issues
2. actual user pain
3. operational bottlenecks

---

## Summary

The backlog is a living document that guides development.

It evolves as the system is tested with real freight operations.