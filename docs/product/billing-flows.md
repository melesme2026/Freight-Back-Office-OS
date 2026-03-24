docs/product/billing-flows.md

# Billing Flows

## Purpose

This document defines how billing flows operate in Freight Back Office OS.

It explains:

- how invoices are created
- how usage is tracked
- how payments are applied
- how billing interacts with operations

---

## Core billing flow

The standard billing lifecycle:

```text
Subscription → Usage → Invoice → Payment → Ledger


⸻

1. Subscription setup flow

Steps
	1.	Create customer account
	2.	Assign service plan
	3.	Create subscription

Customer → ServicePlan → Subscription (active)


⸻

2. Usage tracking flow

Usage is generated from real operations.

Example triggers
	•	load processed → usage record created
	•	driver added → usage record created
	•	premium feature used → usage record created

Load → UsageRecord


⸻

3. Invoice generation flow

Trigger
	•	scheduled job (monthly or cycle-based)
	•	manual trigger (optional)

Steps
	1.	collect subscription
	2.	collect usage records
	3.	calculate totals
	4.	create invoice
	5.	attach line items

Subscription + Usage → Invoice


⸻

Example invoice

Base Fee: $199
Usage: 50 loads × $5 = $250
Total: $449


⸻

4. Invoice lifecycle

draft → open → paid
              ↓
           past_due

States
	•	draft (optional)
	•	open (issued)
	•	paid (completed)
	•	past_due (overdue)

⸻

5. Payment flow

Steps
	1.	payment initiated
	2.	payment processed
	3.	payment applied to invoice
	4.	invoice updated

Payment → Invoice → Ledger


⸻

Payment states

pending → succeeded
pending → failed


⸻

6. Payment application logic

Example

Invoice: $449
Payment: $200

amount_paid = 200
amount_due = 249
status = open


⸻

Full payment

amount_paid = total
amount_due = 0
status = paid


⸻

7. Overdue flow

Trigger
	•	scheduled job checks due dates

Logic

if current_date > due_date and amount_due > 0:
    status = past_due


⸻

Actions
	•	send reminder
	•	flag account
	•	escalate if needed

⸻

8. Refunds (future)

Not fully implemented in V1.

Future flow:

Payment → Refund → Ledger adjustment


⸻

9. Manual billing adjustments

Used when:
	•	invoice error
	•	special pricing
	•	correction needed

Actions
	•	adjust invoice line
	•	add credit or debit entry

⸻

10. Ledger flow

Every financial action creates a ledger entry.

Examples:
	•	invoice created
	•	payment received
	•	adjustment made

Invoice → LedgerEntry
Payment → LedgerEntry


⸻

11. Integration with operations

Billing connects to:
	•	customer account
	•	load activity
	•	usage records

This ensures:
	•	billing reflects real work
	•	no manual mismatch
	•	traceability

⸻

12. Scheduled jobs

Job	Purpose
generate_recurring_invoices	create invoices
mark_overdue_invoices	update overdue status
send_billing_reminders	notify customers
sync_payment_webhooks	reconcile payments


⸻

13. Failure scenarios

Invoice not generated
	•	missing subscription
	•	job did not run

⸻

Incorrect totals
	•	bad usage data
	•	calculation error

⸻

Payment not applied
	•	wrong invoice mapping
	•	processing error

⸻

14. V1 simplifications

In V1:
	•	no tax calculation
	•	no multi-currency
	•	no advanced proration
	•	limited refund handling

Focus is on correctness of flow.

⸻

15. Future enhancements
	•	tax support
	•	discounts and coupons
	•	proration logic
	•	multi-currency
	•	automated retries
	•	billing dashboards

⸻

Summary

Billing flows ensure:
	•	structured revenue generation
	•	clear financial tracking
	•	linkage between operations and billing

They transform operational activity into measurable revenue.

