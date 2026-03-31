docs/runbooks/support-ops.md

# Support Operations Runbook

## Purpose

This runbook defines how to handle support operations in Freight Back Office OS.

It is used by:

- support agents
- operations team
- backend engineers (for escalations)

---

## Support scope

Support tickets may relate to:

- missing or incorrect documents
- load status issues
- extraction or validation errors
- billing and payment issues
- onboarding problems
- system bugs

---

## Core entity

### SupportTicket

Each issue is tracked as a support ticket.

Typical fields:

- subject
- description
- status
- priority
- assigned user
- related entities (load, driver, customer)

---

## Ticket lifecycle

```text
open → in_progress → resolved
        ↓
     escalated

States:
	•	open → newly created
	•	in_progress → actively being worked
	•	resolved → issue fixed
	•	escalated → requires engineering or external support

⸻

Ticket intake

Tickets may come from:
	•	internal staff
	•	customer communication
	•	driver issues
	•	system-generated alerts (future)

⸻

Initial triage checklist

When a ticket is created:
	•	identify issue category
	•	link to load / customer / driver
	•	assign priority
	•	check if blocking operations
	•	assign owner

⸻

Common issue types

1. Missing documents

Symptoms:
	•	load stuck in docs_received
	•	validation errors

Action:
	•	request document from driver
	•	verify upload channel
	•	re-trigger processing

⸻

2. Validation failures

Symptoms:
	•	load in needs_review
	•	blocking validation issues

Action:
	•	review extracted fields
	•	correct manually
	•	resolve validation issues

⸻

3. Load stuck in workflow

Symptoms:
	•	no status change
	•	incomplete processing

Action:
	•	inspect workflow events
	•	check worker logs
	•	manually transition if needed

⸻

4. Billing issues

Symptoms:
	•	incorrect invoice
	•	payment mismatch
	•	missing charges

Action:
	•	inspect invoice lines
	•	verify usage records
	•	apply correction

⸻

5. Onboarding issues

Symptoms:
	•	account not ready
	•	missing steps

Action:
	•	review onboarding checklist
	•	complete missing steps
	•	update status

⸻

6. System errors

Symptoms:
	•	API failure
	•	worker crash
	•	unexpected behavior

Action:
	•	check logs
	•	reproduce issue
	•	escalate to engineering

⸻

Escalation guidelines

Escalate when:
	•	issue cannot be resolved manually
	•	data inconsistency exists
	•	system behavior is incorrect
	•	repeated failures occur

Include:
	•	ticket ID
	•	related load ID
	•	logs or screenshots
	•	steps to reproduce

⸻

Linking tickets to entities

Always link tickets to:
	•	load (if applicable)
	•	customer account
	•	driver

This ensures traceability.

⸻

Resolution checklist

Before closing a ticket:
	•	issue confirmed fixed
	•	related data verified
	•	workflow status updated
	•	customer notified (if needed)

⸻

Monitoring support health

Track:
	•	number of open tickets
	•	average resolution time
	•	recurring issue types
	•	escalations

⸻

Common troubleshooting steps

Check logs

docker compose logs -f api

docker compose logs -f worker


⸻

Check load state
	•	verify status
	•	inspect workflow events
	•	check validation issues

⸻

Check document processing
	•	confirm document exists
	•	confirm classification
	•	confirm extraction ran

⸻

Check billing state
	•	invoice totals
	•	payment records
	•	ledger entries

⸻

Best practices
	•	always document findings
	•	avoid silent fixes
	•	keep tickets linked to entities
	•	communicate clearly with users
	•	escalate early if needed

⸻

Future improvements
	•	automated ticket creation from failures
	•	SLA tracking
	•	support dashboards
	•	AI-assisted support suggestions
	•	customer-facing support portal

⸻

Summary

Support operations are effective when:
	•	issues are resolved quickly
	•	root causes are identified
	•	data remains consistent
	•	communication is clear

This runbook ensures structured and scalable support handling.

---