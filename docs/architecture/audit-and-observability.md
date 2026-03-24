# Audit and Observability

## Purpose

This document explains how Freight Back Office OS tracks important system activity and how operators and engineers observe system behavior.

It covers:

- auditability
- logging
- tracing
- health checks
- operational visibility
- future monitoring direction

---

## Why this matters

A freight back-office system handles operationally sensitive workflows:

- document ingestion
- load status transitions
- validation outcomes
- invoice generation
- payment tracking
- support actions

If something goes wrong, the team must be able to answer:

- what happened
- when it happened
- who changed it
- what system component handled it
- whether the issue is operational, financial, or technical

That is why audit and observability are first-class concerns.

---

## Two different concepts

### Audit

Audit answers:

- who did what
- what changed
- which business record was affected

Audit is primarily about accountability and traceability.

---

### Observability

Observability answers:

- what the system is doing
- whether services are healthy
- why something failed
- where bottlenecks or errors exist

Observability is primarily about system behavior and diagnosis.

---

## Audit architecture

Audit functionality is centered around:

- `AuditLog`
- `WorkflowEvent`
- business records with timestamps
- optional metadata and change payloads

---

## Core audit entities

### AuditLog

Represents a durable record of an auditable system action.

Typical fields include:

- actor_type
- actor_id
- entity_type
- entity_id
- action
- changes_json
- metadata_json

Examples:

- customer account updated
- payment method changed
- subscription cancelled
- invoice status updated
- staff user action recorded

---

### WorkflowEvent

Represents an operational event in the load lifecycle.

Typical examples:

- status changed
- review completed
- exception raised
- document linked

This is separate from `AuditLog` because workflow history is operationally important even when it is not a classic admin or compliance event.

---

## What should be audited

The following changes should be auditable in V1 or soon after:

### Operational actions

- load status changes
- document linking
- extracted field corrections
- validation issue resolution
- support ticket updates

### Commercial actions

- customer account changes
- onboarding updates
- subscription creation and cancellation
- invoice updates
- payment status changes
- ledger adjustments

### Security and access actions

- staff login
- failed auth attempts
- API client activity
- permission-sensitive changes

---

## Audit design principles

### 1. Audit should be append-only in practice

Audit records should not be silently overwritten.

### 2. Audit should record business context

It is not enough to log “updated.”  
The system should show what changed and what entity was involved.

### 3. Audit should support future compliance

Even if V1 is small, the design should support future internal and external accountability.

### 4. Audit should not replace workflow history

Audit and workflow are related but distinct.

---

## Observability architecture

Observability in the system is currently built on:

- structured logging
- health endpoints
- worker logs
- Docker service logs
- readiness checks

Future expansion will include metrics, dashboards, and alerting.

---

## Logging strategy

Logging should exist at several levels.

### API layer

Log:

- incoming request context
- request identifiers
- response status
- unexpected exceptions

### Service layer

Log:

- important orchestration decisions
- workflow transitions
- billing operations
- validation outcomes
- ingestion events

### Worker layer

Log:

- task start
- task success
- task failure
- retry behavior
- queue-related issues

---

## Logging goals

Good logs should help answer:

- which request or task failed
- which load or document was affected
- whether failure came from validation, storage, billing, or infrastructure
- what happened immediately before the error

---

## Request context and correlation

The platform should attach request or operation context whenever possible.

Examples:

- request ID
- actor ID
- organization ID
- load ID
- document ID

This makes logs much more useful during debugging.

---

## Health checks

The system currently includes health-related logic under:

```text
backend/app/core/healthchecks.py

And routes under:

backend/app/api/v1/health.py

Expected health surfaces
	•	liveness
	•	readiness
	•	dependency health

⸻

Liveness

Answers:
	•	is the application process running

Readiness

Answers:
	•	is the application ready to serve traffic
	•	can it reach critical dependencies

Examples:
	•	database connectivity
	•	Redis connectivity
	•	storage readiness

⸻

Dependency visibility

The platform depends on:
	•	PostgreSQL
	•	Redis
	•	filesystem or storage backend
	•	Celery workers
	•	scheduled jobs

Observability should make dependency failures obvious.

⸻

Worker observability

Celery tasks must be observable because many important operations are asynchronous.

Examples:
	•	document processing
	•	extraction
	•	validation
	•	invoice generation
	•	payment sync
	•	reminders

Minimum visibility needed:
	•	task name
	•	input identifiers
	•	enqueue time
	•	success/failure
	•	error details

⸻

Billing observability

Billing behavior is high-risk and must be observable.

Important billing signals include:
	•	invoices generated
	•	invoice totals
	•	payment success/failure
	•	overdue invoice counts
	•	reminder runs
	•	webhook processing outcomes

⸻

Ingestion observability

Ingestion is the front door of the system, so it must be easy to inspect.

Important signals include:
	•	webhook received
	•	upload accepted
	•	sender identified
	•	document created
	•	duplicate detected
	•	processing triggered

⸻

Operational dashboards, future direction

A future observability layer should include dashboards for:

Operations dashboard
	•	loads by status
	•	review queue volume
	•	validation issues by type
	•	document processing times

Billing dashboard
	•	invoices created
	•	open invoices
	•	paid invoices
	•	overdue invoices
	•	payment success rate

Ingestion dashboard
	•	documents received by channel
	•	ingestion failure rate
	•	duplicate submissions
	•	OCR and extraction turnaround

Support dashboard
	•	open tickets
	•	escalations
	•	recurring issue categories

⸻

Alerting, future direction

Eventually the platform should alert on:
	•	API downtime
	•	worker crashes
	•	database connectivity failures
	•	invoice generation failures
	•	repeated payment webhook failures
	•	abnormal spike in validation failures
	•	backlog growth in processing queues

Possible future channels:
	•	email
	•	Slack
	•	SMS
	•	internal admin notifications

⸻

What is acceptable in V1

For V1, the following is acceptable:
	•	structured logs
	•	basic health endpoints
	•	Docker/container logs
	•	manual inspection of worker output
	•	audit records for major business changes

This is enough for early validation and testing.

⸻

What should come after V1

After real workflows are proven, observability should evolve toward:
	•	centralized logging
	•	metrics and dashboards
	•	request tracing
	•	worker queue monitoring
	•	alerting
	•	billing anomaly alerts
	•	support trend reporting

Possible future tools:
	•	Prometheus
	•	Grafana
	•	Loki
	•	ELK stack
	•	Datadog
	•	Sentry

⸻

Risks of weak audit and observability

If audit is weak:
	•	business changes are hard to explain
	•	accountability is poor
	•	financial disputes become harder

If observability is weak:
	•	errors take too long to diagnose
	•	worker failures go unnoticed
	•	billing issues can accumulate silently
	•	support load increases

That is why both matter early, even in V1.

⸻

Design principles summary

Audit principles
	•	explicit
	•	durable
	•	business-aware
	•	actor-aware

Observability principles
	•	structured
	•	contextual
	•	dependency-aware
	•	useful during failure, not just during success

⸻

Summary

Audit and observability are essential to making Freight Back Office OS a trustworthy operational platform.

Audit ensures the business can answer:
	•	who changed what

Observability ensures the team can answer:
	•	what the system is doing
	•	what failed
	•	why it failed

Together, they make the platform diagnosable, accountable, and scalable.

