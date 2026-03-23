Paste this into:

docs/architecture/workflow-engine.md

# Workflow Engine

## Overview

The workflow engine controls how a **Load** moves through its lifecycle in a predictable, auditable, and enforceable way.

Instead of informal status updates (e.g., spreadsheets or chat messages), the system enforces a **state machine** that defines:

- what states exist
- which transitions are allowed
- what side effects occur during transitions
- how transitions are recorded

This ensures operational consistency and traceability.

---

## Why a workflow engine is needed

In a manual freight back-office process:

- different people interpret "ready" differently
- loads jump from incomplete → invoiced incorrectly
- missing documents are overlooked
- no consistent record exists of what happened

The workflow engine solves this by:

- enforcing valid transitions
- centralizing state logic
- recording all transitions as events
- enabling automation triggers

---

## Core components

The workflow system is composed of:

### 1. LoadStatus (state enum)

Represents the lifecycle states of a load.

Typical states:

- `new`
- `docs_received`
- `extracting`
- `needs_review`
- `validated`
- `ready_to_submit`
- `submitted`
- `funded`
- `paid`
- `exception`
- `archived`

---

### 2. LoadStateMachine

This defines **allowed transitions**.

Example:

```text
new → docs_received
docs_received → extracting
extracting → needs_review
needs_review → validated
validated → ready_to_submit
ready_to_submit → submitted
submitted → funded
funded → paid

Invalid example:

new → paid  ❌

The state machine enforces rules like:

can_transition(current_status, new_status) -> bool


⸻

3. LoadTransitionApplier

This applies the transition and handles side effects.

Examples of side effects:

Transition	Side Effect
→ submitted	set submitted_at
→ funded	set funded_at
→ paid	set paid_at
→ validated	set processing_status = completed
→ exception	set processing_status = failed


⸻

4. WorkflowEngine

This is the orchestration layer.

Responsibilities:
	•	validate transition using state machine
	•	apply transition using transition applier
	•	persist updated load
	•	create WorkflowEvent

⸻

5. WorkflowEvent

Every transition creates a record:

Example:

{
  "event_type": "status_changed",
  "old_status": "docs_received",
  "new_status": "extracting",
  "actor_type": "system",
  "created_at": "..."
}

This enables:
	•	auditability
	•	debugging
	•	timeline reconstruction

⸻

Transition flow

Example: document received → review → validated

Driver uploads documents
        ↓
Load: new → docs_received
        ↓
System triggers extraction
        ↓
Load: docs_received → extracting
        ↓
Extraction completes
        ↓
Load: extracting → needs_review
        ↓
Staff reviews and fixes data
        ↓
Load: needs_review → validated


⸻

Transition validation rules

Each transition must pass:
	1.	State rule (allowed path)
	2.	Business rule (optional)

Examples:

Allowed transition

can_transition("new", "docs_received") == True

Blocked transition

can_transition("new", "paid") == False

Business validation (future)
	•	cannot move to validated if blocking validation issues exist
	•	cannot move to submitted if required documents missing
	•	cannot move to funded without submission timestamp

⸻

Processing status vs load status

Two concepts exist:

Load Status (business lifecycle)
	•	where the load is operationally

Processing Status (system state)
	•	pending
	•	processing
	•	completed
	•	failed

Example:

LoadStatus = validated
ProcessingStatus = completed

LoadStatus = exception
ProcessingStatus = failed


⸻

Integration with validation system

The workflow engine interacts with validation:

Flow:

Extraction → Validation → Decision

If validation issues exist:

→ needs_review

If no issues:

→ validated

Blocking issues prevent forward movement.

⸻

Integration with documents

Document events trigger transitions:

Event	Transition
document uploaded	new → docs_received
classification complete	docs_received → extracting
extraction complete	extracting → needs_review


⸻

Integration with billing

Later transitions connect to billing:

State	Billing relevance
validated	ready for invoice
submitted	operationally complete
funded	payment expected
paid	revenue realized


⸻

Exception handling

Any step can trigger:

→ exception

This is used for:
	•	validation failure
	•	system failure
	•	manual escalation

Effects:
	•	processing_status = failed
	•	requires manual intervention

⸻

Review loop

Loads can cycle:

needs_review → validated → needs_review

Example:
	•	reviewer fixes data
	•	new validation detects issue
	•	back to review

This supports iterative correction.

⸻

Auditability

Every transition is recorded:
	•	who triggered it
	•	when it happened
	•	from → to
	•	optional payload

This allows:
	•	debugging
	•	compliance
	•	dispute resolution
	•	analytics

⸻

Why this design is important

Without a workflow engine:
	•	state is inconsistent
	•	logic is scattered
	•	bugs are hard to trace
	•	automation is fragile

With this design:
	•	all transitions are centralized
	•	rules are enforceable
	•	behavior is predictable
	•	future automation becomes easy

⸻

Future enhancements

The workflow engine can evolve with:

1. Guard conditions

if has_blocking_issues:
    block_transition()

2. Event-driven triggers
	•	Kafka / PubSub events
	•	async workflows

3. SLA tracking
	•	time in each state
	•	escalation triggers

4. Parallel states
	•	document processing independent of billing

5. Retry logic
	•	failed extraction retry
	•	webhook retry

⸻

Summary

The workflow engine is the control center of load operations.

It ensures:
	•	loads move correctly
	•	rules are enforced
	•	actions are recorded
	•	automation can be layered safely

It transforms the system from a passive database into an active operational engine.

