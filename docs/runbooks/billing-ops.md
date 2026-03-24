Paste this into:

docs/runbooks/billing-ops.md

# Billing Operations Runbook

## Purpose

This runbook defines how to operate, monitor, and troubleshoot the billing system in Freight Back Office OS.

It is used by:

- operations / finance
- support team
- backend engineers

---

## Billing components recap

The billing system includes:

- Service Plans
- Subscriptions
- Usage Records
- Invoices
- Payments
- Ledger Entries

---

## Daily billing operations

### 1. Verify invoice generation

Check that recurring invoices were generated.

Expected behavior:

- subscriptions generate invoices on schedule
- invoices include base + usage

Validation:

- invoice count increased
- invoice totals match usage

---

### 2. Monitor payment activity

Check:

- new payments recorded
- failed payments logged
- partial payments handled correctly

---

### 3. Review overdue invoices

Run:

- identify invoices in `past_due`

Actions:

- trigger reminders
- flag accounts if needed

---

## Key workflows

### Subscription lifecycle

```text
active → cancelled
active → past_due (if unpaid behavior added later)


⸻

Invoice lifecycle

open → paid
open → past_due


⸻

Payment lifecycle

pending → succeeded
pending → failed


⸻

Invoice validation checklist

For each invoice:
	•	correct customer account
	•	correct billing period
	•	base fee applied
	•	usage charges correct
	•	totals match expected values

⸻

Payment validation checklist

For each payment:
	•	amount <= amount_due
	•	correct invoice linked
	•	status updated
	•	timestamps recorded

⸻

Common operations

Regenerate invoice (manual fix)

If invoice is incorrect:
	1.	mark existing invoice as void (future enhancement)
	2.	regenerate using correct usage data

(Currently manual logic may be required)

⸻

Apply manual payment

payment_service.collect_payment(...)

Used when:
	•	offline payment received
	•	manual adjustment needed

⸻

Mark invoice as past due

invoice_service.mark_past_due(...)

Used by scheduled jobs or manual intervention.

⸻

Scheduled jobs (Celery)

These should run automatically:

Job	Purpose
generate_recurring_invoices	create invoices
mark_overdue_invoices	update status
send_billing_reminders	notify customers
sync_payment_webhooks	reconcile external payments


⸻

Monitoring

What to watch daily
	•	number of invoices created
	•	payment success rate
	•	failed payments
	•	overdue invoices

⸻

Warning signs
	•	no invoices generated
	•	payments not reducing balances
	•	negative or incorrect totals
	•	repeated payment failures

⸻

Troubleshooting

Issue: Invoice not generated

Check:
	•	subscription exists
	•	billing cycle active
	•	scheduled job ran

⸻

Issue: Incorrect totals

Check:
	•	usage records
	•	line item calculation
	•	rounding logic

⸻

Issue: Payment not applied

Check:
	•	payment linked to correct invoice
	•	amount calculation
	•	service logic

⸻

Issue: Overpayment error

Expected behavior:

payment > amount_due → reject

Fix:
	•	adjust payment amount
	•	split into correct values

⸻

Manual recovery steps

Fix broken invoice
	1.	inspect invoice lines
	2.	recalculate expected totals
	3.	correct manually via service

⸻

Fix missing payment
	1.	verify external provider
	2.	reprocess webhook (future)
	3.	manually apply payment

⸻

Audit and traceability

Every billing action should be traceable via:
	•	invoice records
	•	payment records
	•	ledger entries

Future:
	•	audit logs for all billing changes

⸻

Future improvements
	•	automated retries for failed payments
	•	refund handling
	•	invoice voiding
	•	credit notes
	•	tax calculation
	•	multi-currency support
	•	billing dashboard analytics

⸻

Summary

Billing operations are healthy when:
	•	invoices generate correctly
	•	payments update balances
	•	overdue invoices are tracked
	•	no mismatches exist

This runbook ensures consistent financial handling and supports scaling into a real SaaS billing system.

---

## Next file (aligned with your structure)

```text
docs/runbooks/support-ops.md