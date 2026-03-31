# Onboarding Architecture

## Purpose

This document explains how onboarding is modeled and handled in Freight Back Office OS.

It covers:

* onboarding domain structure
* onboarding lifecycle
* how onboarding connects to operations and billing
* why onboarding is a first-class part of the platform

---

## Why onboarding matters

In many small freight operations, onboarding is informal.

It often happens through:

* text messages
* phone calls
* spreadsheets
* memory
* ad hoc notes

That creates problems:

* customers go live before they are ready
* billing starts without correct setup
* drivers are not configured properly
* ingestion channels are not connected
* support issues begin before operations are stable

The system solves this by making onboarding explicit and trackable.

---

## Core onboarding model

The onboarding architecture is centered on:

* `CustomerAccount`
* `OnboardingChecklist`
* `Referral`
* `ServicePlan`
* `Subscription`
* `PaymentMethod`
* `Driver`

These entities work together to move a customer from prospect to operational readiness.

---

## Main onboarding entities

### CustomerAccount

Represents the customer relationship.

This is the anchor record for onboarding.

It stores:

* account identity
* contact details
* billing information
* current status
* notes

---

### OnboardingChecklist

Represents structured go-live readiness.

It captures whether key onboarding steps are complete.

Typical fields:

* `documents_received`
* `pricing_confirmed`
* `payment_method_added`
* `driver_profiles_created`
* `channel_connected`
* `go_live_ready`

This record exists so onboarding is not hidden in notes or memory.

---

### Referral

Represents lead source or referral context.

Useful for:

* tracking how the customer arrived
* future partner reporting
* sales or referral workflows later

---

### ServicePlan and Subscription

These connect onboarding to commercial readiness.

A customer is not fully ready until pricing is defined and a billing model exists.

---

### PaymentMethod

Represents billing readiness.

Without a payment method, a customer may be operationally active but commercially incomplete.

---

### Driver

Drivers often need to be created before true go-live, especially if document ingestion depends on them.

---

## Onboarding lifecycle

The checklist typically moves through these statuses:

```text
not_started -> in_progress -> completed
```

Conceptually, business readiness often looks like:

```text
lead -> customer_created -> onboarding_in_progress -> go_live_ready -> active
```

---

## Step-by-step onboarding architecture

### Step 1: Customer account creation

A new customer is created in the system.

This establishes:

* tenant-scoped customer identity
* contact details
* account relationship
* billing contact fields

At this stage, the customer is known to the system but not yet ready.

### Step 2: Checklist initialization

When onboarding begins, the system creates or initializes an `OnboardingChecklist`.

This gives the team a structured readiness tracker instead of scattered notes.

Initial state:

* `status = not_started`
* all readiness flags = `false`

### Step 3: Commercial alignment

The team confirms:

* pricing terms
* service plan
* subscription model
* billing contact

This corresponds to:

* `pricing_confirmed`
* subscription creation
* future invoice readiness

### Step 4: Payment readiness

The customer provides a payment method or billing arrangement.

This corresponds to:

* `payment_method_added`

Even if the system supports manual billing in early phases, this field still matters for readiness tracking.

### Step 5: Driver and operations setup

The team creates required driver records and any operational mappings needed for day-to-day work.

This corresponds to:

* `driver_profiles_created`

If the business depends on driver document submission, this is essential.

### Step 6: Channel connection

The customer's operational ingestion path must be ready.

Examples:

* manual upload process defined
* WhatsApp number known and tested
* future email channel configured

This corresponds to:

* `channel_connected`

### Step 7: Document readiness

The team verifies that required onboarding documents or initial operational paperwork has been received.

This corresponds to:

* `documents_received`

This is separate from daily load document processing. It focuses on readiness to operate.

### Step 8: Go-live decision

Once all required readiness fields are satisfied:

```text
go_live_ready = true
status = completed
```

This indicates that the customer can safely begin active operational use.

---

## Architectural flow

```text
Referral or Lead
    ↓
CustomerAccount created
    ↓
OnboardingChecklist initialized
    ↓
Pricing confirmed
    ↓
Payment method added
    ↓
Drivers created
    ↓
Channel connected
    ↓
Required documents received
    ↓
Go-live ready
    ↓
Operational usage begins
```

---

## Separation of onboarding from operations

A key design decision is that onboarding is separate from the load workflow.

Why this matters:

* readiness becomes unclear if onboarding is mixed directly into load processing
* billing setup gets forgotten
* operational issues show up too late
* support load increases

By separating onboarding:

* the customer can be made ready before active usage
* go-live becomes measurable
* readiness can be audited

---

## Separation of onboarding from billing

Onboarding and billing are linked, but not identical.

Onboarding answers:

* is this customer ready to use the system?

Billing answers:

* how will this customer be charged?

This separation allows:

* operational readiness before full billing automation
* staged rollout
* commercial flexibility

---

## Service-layer architecture

Onboarding logic currently lives under:

```text
backend/app/services/onboarding/
```

Key files:

* `onboarding_service.py`
* `customer_account_service.py`
* `referral_service.py`

Responsibilities:

### OnboardingService

* initialize the checklist
* retrieve the checklist
* update readiness fields
* determine completion status

### CustomerAccountService

* create and manage customer accounts
* validate uniqueness rules
* update account data

### ReferralService

* create and manage referral records
* support lead source tracking

---

## API-layer architecture

Relevant route modules include:

* `backend/app/api/v1/customer_accounts.py`
* `backend/app/api/v1/onboarding.py`
* `backend/app/api/v1/referrals.py`
* `backend/app/api/v1/service_plans.py`
* `backend/app/api/v1/subscriptions.py`
* `backend/app/api/v1/payments.py`

This separation allows the frontend and future automations to interact with onboarding as a dedicated workflow.

---

## Example V1 onboarding scenario

A new freight customer is added.

1. Staff creates `CustomerAccount`
2. System initializes `OnboardingChecklist`
3. Staff confirms pricing and selects a plan
4. Staff adds billing email and payment setup
5. Drivers are created
6. Upload or WhatsApp channel process is agreed
7. Initial required documents are received
8. `go_live_ready` becomes `true`
9. Customer starts using the load workflow

This is the practical bridge from lead to real usage.

---

## Current V1 simplifications

In V1, onboarding is intentionally simple.

Present limitations:

* mostly manual step completion
* no automated onboarding wizard
* no self-serve customer onboarding
* no SLA tracking
* no reminder automation yet
* no document-specific onboarding packs yet

That is acceptable for this stage because the focus is correctness and structure.

---

## Future enhancements

Likely onboarding improvements include:

* onboarding dashboard
* guided onboarding wizard
* automated reminders for incomplete steps
* role-based onboarding responsibilities
* self-serve customer setup
* onboarding document packs
* channel connection testing workflows
* onboarding analytics
* activation approvals

---

## Design principles

### 1. Explicit readiness is better than assumptions

No customer should be considered live just because someone said they are ready.

### 2. Operational and commercial readiness both matter

A customer is not truly ready if the team cannot process documents or bill correctly.

### 3. Onboarding should be auditable

The system should show what has and has not been completed.

### 4. Onboarding should support future scale

Even if V1 is for a small real-world workflow today, the architecture must support many customers later.

---

## Risks if onboarding is weak

If onboarding is not structured:

* customers go live too early
* billing gets delayed
* support issues increase
* operations become inconsistent
* trust in the system drops

That is why onboarding deserves its own architecture.

---

## Summary

The onboarding architecture ensures that a customer becomes operationally and commercially ready in a structured way.

It gives the system a controlled bridge between:

* prospect or referral
* customer setup
* billing readiness
* live operational use

Without this layer, the platform would have strong operations code but weak customer activation discipline.
