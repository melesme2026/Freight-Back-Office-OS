Paste this into:

docs/architecture/billing-system.md

# Billing System

## Overview

The billing system is responsible for monetizing the freight back-office operations in a structured, auditable, and scalable way.

It supports both:

- subscription-based pricing (SaaS model)
- usage-based billing (per load, per driver, etc.)

The design separates billing from operations while still allowing tight linkage to real-world activity.

---

## Why billing is a separate domain

In a manual workflow:

- invoices are created ad hoc
- payments are tracked in spreadsheets
- no consistent pricing model exists
- no linkage between usage and revenue

By separating billing into its own domain:

- pricing becomes structured
- revenue becomes predictable
- usage can be measured
- financial records become auditable

---

## Core billing entities

### 1. ServicePlan

Represents a pricing plan.

Examples:

- Starter plan
- Growth plan
- Enterprise plan

Typical attributes:

- name
- code
- billing cycle (monthly, yearly)
- base price
- per-load price
- per-driver price
- active flag

---

### 2. Subscription

Represents a customer’s enrollment in a plan.

Typical attributes:

- customer account
- service plan
- status (active, cancelled, etc.)
- billing period start/end
- cancel at period end
- billing email

A customer account can have one or more subscriptions.

---

### 3. UsageRecord

Tracks billable activity.

Examples:

- number of loads processed
- number of drivers onboarded
- premium features used

Typical attributes:

- usage type
- quantity
- unit price
- usage date
- metadata

---

### 4. BillingInvoice

Represents an invoice issued to a customer.

Typical attributes:

- invoice number
- status (draft, open, paid, past_due)
- subtotal
- tax
- total
- amount paid
- amount due
- issued date
- due date
- paid date

---

### 5. BillingInvoiceLine

Represents individual line items on an invoice.

Examples:

- base subscription fee
- per-load usage
- adjustments

---

### 6. PaymentMethod

Represents stored payment details.

Examples:

- card (last4, brand)
- external provider reference (Stripe, etc.)

---

### 7. Payment

Represents a payment attempt or success.

Typical attributes:

- amount
- currency
- status (pending, succeeded, failed)
- timestamps
- failure reason

---

### 8. LedgerEntry

Represents financial accounting entries.

Examples:

- invoice posted
- payment applied
- adjustment made

This is the source of truth for financial audit.

---

## Billing flow

### Step 1: Subscription creation

```text
CustomerAccount → Subscription → ServicePlan

The customer is assigned a pricing model.

⸻

Step 2: Usage tracking

Load activity → UsageRecord

Examples:
	•	each load processed adds usage
	•	premium features increment usage

⸻

Step 3: Invoice generation

Recurring job:

Subscription + Usage → Invoice

Invoice contains:
	•	base fee
	•	usage charges
	•	totals

⸻

Step 4: Payment collection

Invoice → Payment → Ledger

Payment updates:
	•	invoice amount_paid
	•	invoice amount_due
	•	invoice status

⸻

Step 5: Overdue handling

Unpaid invoice → past_due

Triggers:
	•	reminders
	•	notifications
	•	potential account actions (future)

⸻

Invoice lifecycle

draft → open → paid
              ↓
           past_due

States:
	•	draft (optional future)
	•	open (issued but unpaid)
	•	paid
	•	past_due

⸻

Payment lifecycle

pending → succeeded
        → failed

Effects:
	•	succeeded → updates invoice
	•	failed → recorded for retry or manual follow-up

⸻

Integration with loads

Billing connects to operations via:
	•	load → usage record
	•	customer account → subscription
	•	invoice → customer account

This ensures:
	•	revenue reflects real work
	•	no double counting
	•	traceability from load → invoice → payment

⸻

Recurring jobs (Celery)

The system uses scheduled jobs:

Job	Purpose
generate_recurring_invoices	create invoices from subscriptions
mark_overdue_invoices	update overdue status
send_billing_reminders	notify customers
sync_payment_webhooks	reconcile external payments


⸻

Payment providers (future)

Currently placeholder-based.

Future integrations:
	•	Stripe
	•	QuickBooks
	•	ACH systems
	•	factoring integrations

The system is designed so provider logic is abstracted behind services.

⸻

Design decisions

1. Separation from Load

Loads do NOT directly contain billing logic.

Why:
	•	keeps operational logic clean
	•	allows flexible pricing models
	•	avoids tight coupling

⸻

2. Ledger-based accounting

Every financial change should produce a ledger entry.

Benefits:
	•	auditability
	•	financial traceability
	•	reconciliation support

⸻

3. Partial payments supported

Invoices can be:
	•	partially paid
	•	fully paid
	•	unpaid

⸻

4. Overpayment prevention

The system prevents:

payment > amount_due


⸻

Example scenario

Scenario: Monthly subscription + usage

Customer:
  Starter Plan ($99/month)
  10 loads processed
  $5 per load

Invoice:

Base: $99
Usage: 10 × $5 = $50
Total: $149

Payment:

Paid: $100
Remaining: $49
Status: open


⸻

Future enhancements
	•	tax calculation
	•	discounts and coupons
	•	proration
	•	multi-currency support
	•	invoice PDF generation
	•	automated retries for failed payments
	•	payment reconciliation dashboards
	•	revenue analytics

⸻

Summary

The billing system converts operational activity into structured revenue.

It ensures:
	•	consistent pricing
	•	automated invoicing
	•	accurate payment tracking
	•	financial auditability

It is a core pillar for turning this platform into a real business.

After you commit that, the next file is:

```text
docs/setup/local-development.md