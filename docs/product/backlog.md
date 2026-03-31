# Product Backlog

## Purpose

This backlog captures all known and anticipated work for Freight Back Office OS.

It includes:

- Features
- Improvements
- Technical debt
- Future ideas

Items are grouped by priority and phase.

---

## Priority Levels

- **P0** → Critical (must have for V1 validation)
- **P1** → High (needed soon after V1)
- **P2** → Medium (important but not urgent)
- **P3** → Low (future or nice to have)

---

## P0 — Critical (V1 validation)

These are required to make the system usable with real paperwork.

### Core Workflow

- [ ] Upload real documents (rate confirmation, BOL, invoice)
- [ ] Link documents to loads correctly
- [ ] Ensure load lifecycle works end to end
- [ ] Ensure workflow transitions are correct

---

### Extraction

- [ ] Identify real fields from actual documents
- [ ] Improve `extraction_service` based on real samples
- [ ] Handle missing or unclear fields gracefully

---

### Validation

- [ ] Ensure validation rules match real-world issues
- [ ] Add missing rules discovered during testing
- [ ] Ensure blocking vs. non-blocking logic is correct

---

### Review Flow

- [ ] Ensure review queue shows real issues clearly
- [ ] Add ability to correct extracted fields
- [ ] Add ability to resolve validation issues

---

### Stability

- [ ] Fix any crashes during document processing
- [ ] Ensure worker tasks complete reliably
- [ ] Ensure no data loss

---

## P1 — High Priority

These improve usability and reduce manual effort.

### Automation

- [ ] Improve document auto-classification accuracy
- [ ] Auto-link documents to loads
- [ ] Improve load matching logic

---

### Notifications

- [ ] Notify driver when a document is missing
- [ ] Notify when a load is ready
- [ ] Notify on validation issues

---

### Billing

- [ ] Improve invoice generation accuracy
- [ ] Ensure usage tracking is correct
- [ ] Improve payment handling

---

### UI (Basic)

- [ ] Complete load list page
- [ ] Complete load detail page
- [ ] Complete review queue UI
- [ ] Complete document viewer

---

## P2 — Medium Priority

These support scaling and better operations.

### Onboarding

- [ ] Improve onboarding checklist logic
- [ ] Add onboarding UI
- [ ] Track onboarding progress visually

---

### Reporting

- [ ] Add basic dashboard metrics
- [ ] Add load counts
- [ ] Add billing totals
- [ ] Add processing time metrics

---

### Support

- [ ] Improve support ticket workflow
- [ ] Add better ticket filtering
- [ ] Link tickets more tightly to loads

---

### API Improvements

- [ ] Add filtering and search
- [ ] Improve pagination
- [ ] Add better error messages

---

## P3 — Low Priority / Future

These are long-term improvements.

### AI

- [ ] Improve extraction accuracy using real datasets
- [ ] Add anomaly detection improvements
- [ ] Suggest corrections automatically

---

### Billing Advanced

- [ ] Add discounts and coupons
- [ ] Add tax calculation
- [ ] Add multi-currency support
- [ ] Add refund handling

---

### Platform

- [ ] Improve multi-tenant isolation
- [ ] Add role-based access control
- [ ] Add API rate limiting

---

### Integrations

- [ ] Add Stripe integration
- [ ] Add QuickBooks integration
- [ ] Add factoring system integrations

---

## Tech Debt

- [ ] Clean up placeholder services
- [ ] Refactor duplicated logic
- [ ] Improve logging consistency
- [ ] Improve error handling
- [ ] Improve test coverage

---

## Ideas / Future Exploration

- [ ] Improve driver mobile experience
- [ ] Add AI assistant for support
- [ ] Add automatic load reconciliation
- [ ] Add predictive billing insights

---

## Backlog Usage

This backlog should be:

- Reviewed weekly
- Updated after real workflow testing
- Refined based on actual pain points

---

## Key Rule

Do not blindly build from the backlog.

Always prioritize based on:

1. Real workflow issues
2. Actual user pain
3. Operational bottlenecks

---

## Summary

The backlog is a living document that guides development.

It should evolve as the system is tested with real freight operations.