docs/product/onboarding-flows.md

# Onboarding Flows

## Purpose

This document defines how customer onboarding works in Freight Back Office OS.

It explains:

- how new customers are introduced into the system
- how readiness is tracked
- how onboarding connects to operations and billing
- what steps are required before a customer goes live

---

## Core onboarding flow

```text
Lead → Customer Account → Onboarding Checklist → Ready → Active Operations


⸻

1. Customer creation flow

Steps
	1.	Create customer account
	2.	Assign basic details
	3.	Initialize onboarding checklist

CustomerAccount (created) → OnboardingChecklist (initialized)


⸻

2. Onboarding checklist structure

Each customer has a structured checklist.

Example fields
	•	documents_received
	•	pricing_confirmed
	•	payment_method_added
	•	drivers_created
	•	channel_connected
	•	go_live_ready

⸻

3. Onboarding lifecycle

not_started → in_progress → ready → active

States
	•	not_started → checklist initialized
	•	in_progress → steps being completed
	•	ready → all required steps complete
	•	active → customer fully operational

⸻

4. Step completion flow

Each onboarding step is updated individually.

Example

documents_received = true
pricing_confirmed = true
payment_method_added = false

System evaluates:

if all_required_steps_complete:
    status = ready


⸻

5. Driver setup flow

Steps
	1.	create driver records
	2.	assign to customer account
	3.	validate contact info

Customer → Drivers → Ready for document ingestion


⸻

6. Channel connection flow

Channels
	•	WhatsApp (primary)
	•	Email (future)
	•	API (future)

Flow

Connect channel → Validate → Ready for ingestion


⸻

7. Pricing confirmation flow

Steps
	1.	select service plan
	2.	confirm pricing terms
	3.	create subscription

Customer → ServicePlan → Subscription


⸻

8. Payment setup flow

Steps
	1.	add payment method
	2.	validate payment method
	3.	link to customer account

⸻

9. Go-live decision

Customer becomes ready when:
	•	documents flow is understood
	•	drivers are set up
	•	pricing is confirmed
	•	payment method exists
	•	channel is connected

Checklist complete → go_live_ready = true


⸻

10. Transition to active operations

ready → active

Once active:
	•	loads can be processed
	•	billing can be applied
	•	documents can be ingested

⸻

11. Common onboarding issues

Missing drivers
	•	no document source
	•	ingestion cannot start

⸻

No payment method
	•	billing cannot proceed

⸻

Incomplete checklist
	•	customer not ready for live usage

⸻

Channel not connected
	•	no document ingestion

⸻

12. Support involvement

Support may:
	•	assist onboarding steps
	•	resolve issues
	•	guide customer setup

⸻

13. V1 simplifications

In V1:
	•	onboarding is manual
	•	no automated flows
	•	no self-serve onboarding UI
	•	checklist is basic

Focus is on correctness, not automation.

⸻

14. Future enhancements
	•	self-service onboarding
	•	automated checklist progression
	•	onboarding dashboards
	•	onboarding notifications
	•	guided workflows

⸻

Summary

Onboarding ensures:
	•	customers are properly set up
	•	operations can run smoothly
	•	billing can be applied correctly

It is the bridge between a new customer and real system usage.

