# Billing Architecture

## Overview

The billing domain is responsible for monetizing freight back-office operations in a structured, auditable, and scalable way.

It supports both:

* subscription-based pricing (SaaS model)
* usage-based billing (per load, per driver, and similar operational units)

The design keeps billing separate from operations while still allowing tight linkage to real-world activity.

---

## Why billing is a separate domain

In a manual workflow:

* invoices are created ad hoc
* payments are tracked in spreadsheets
* no consistent pricing model exists
* no reliable linkage between usage and revenue exists

By separating billing into its own domain:

* pricing becomes structured
* revenue becomes more predictable
* usage can be measured cleanly
* financial records become auditable

---

## Core billing entities

### 1. ServicePlan

Represents a pricing plan.

Examples:

* Starter plan
* Growth plan
* Enterprise plan

Typical attributes:

* name
* code
* billing cycle (`monthly`, `yearly`)
* base price
* per-load price
* per-driver price
* active flag

---

### 2. Subscription

Represents a customer account's enrollment in a plan.

Typical attributes:

* customer account
* service plan
* status (`active`, `cancelled`, and related lifecycle states)
* billing period start and end
* cancel at period end
* billing email

A customer account can have one or more subscriptions depending on the business model.

---

### 3. UsageRecord

Tracks billable activity.

Examples:

* number of loads processed
* number of drivers onboarded
* premium features used

Typical attributes:

* usage type
* quantity
* unit price
* usage date
* metadata

---

### 4. BillingInvoice

Represents an invoice issued to a customer.

Typical attributes:

* invoice number
* status (`draft`, `open`, `paid`, `past_due`)
* subtotal
* tax
* total
* amount paid
* amount due
* issued date
* due date
* paid date

---

### 5. BillingInvoiceLine

Represents an individual line item on an invoice.

Examples:

* base subscription fee
* per-load usage
* adjustments

---

### 6. PaymentMethod

Represents stored payment details.

Examples:

* card metadata such as last4 and brand
* external provider reference such as Stripe payment method identifiers

---

### 7. Payment

Represents a payment attempt or completed payment.

Typical attributes:

* amount
* currency
* status (`pending`, `succeeded`, `failed`)
* timestamps
* failure reason

---

### 8. LedgerEntry

Represents financial accounting entries.

Examples:

* invoice posted
* payment applied
* adjustment made

This should be treated as a source of truth for financial audit and reconciliation.

---

## Billing flow

### Step 1: Subscription creation

```text
CustomerAccount -> Subscription -> ServicePlan
```

The customer is assigned a pricing model.

### Step 2: Usage tracking

```text
Load activity -> UsageRecord
```

Examples:

* each processed load adds usage
* premium features increment usage

### Step 3: Invoice generation

Recurring job:

```text
Subscription + Usage -> Invoice
```

The invoice contains:

* base fee
* usage charges
* totals

### Step 4: Payment collection

```text
Invoice -> Payment -> Ledger
```

Payment updates:

* invoice `amount_paid`
* invoice `amount_due`
* invoice `status`

### Step 5: Overdue handling

```text
Unpaid invoice -> past_due
```

This can trigger:

* reminders
* notifications
* potential account actions in a future phase

---

## Invoice lifecycle

```text
draft -> open -> paid
              \
               -> past_due
```

States:

* `draft` (optional in a future phase)
* `open` (issued but unpaid)
* `paid`
* `past_due`

---

## Payment lifecycle

```text
pending -> succeeded
        -> failed
```

Effects:

* `succeeded` updates invoice balances and status
* `failed` is recorded for retry or manual follow-up

---

## Integration with loads

Billing connects to operations through:

* `load` -> usage record
* `customer account` -> subscription
* `invoice` -> customer account

This ensures:

* revenue reflects real work
* double counting is reduced or prevented
* traceability exists from load to invoice to payment

---

## Recurring jobs (Celery)

The system uses scheduled jobs such as:

| Job                           | Purpose                                      |
| ----------------------------- | -------------------------------------------- |
| `generate_recurring_invoices` | Create invoices from subscriptions and usage |
| `mark_overdue_invoices`       | Update overdue status                        |
| `send_billing_reminders`      | Notify customers                             |
| `sync_payment_webhooks`       | Reconcile external payments                  |

---

## Payment providers (future)

The current design is placeholder-friendly.

Future integrations may include:

* Stripe
* QuickBooks
* ACH systems
* factoring integrations

Provider-specific behavior should remain abstracted behind billing services.

---

## Design decisions

### 1. Separation from load operations

Loads should not directly contain billing logic.

Why:

* keeps operational logic clean
* allows flexible pricing models
* avoids tight coupling

### 2. Ledger-based accounting

Every financial change should produce a ledger entry.

Benefits:

* auditability
* financial traceability
* reconciliation support

### 3. Partial payments supported

Invoices can be:

* partially paid
* fully paid
* unpaid

### 4. Overpayment prevention

The system should prevent this condition:

```text
payment > amount_due
```

---

## Example scenario

### Scenario: Monthly subscription plus usage

Customer:

```text
Starter Plan ($99/month)
10 loads processed
$5 per load
```

Invoice:

```text
Base: $99
Usage: 10 x $5 = $50
Total: $149
```

Payment:

```text
Paid: $100
Remaining: $49
Status: open
```

---

## Future enhancements

* tax calculation
* discounts and coupons
* proration
* multi-currency support
* invoice PDF generation
* automated retries for failed payments
* payment reconciliation dashboards
* revenue analytics

---

## Summary

The billing domain converts operational activity into structured revenue.

It helps ensure:

* consistent pricing
* automated invoicing
* accurate payment tracking
* financial auditability

It is a core pillar for turning this platform into a real business.
