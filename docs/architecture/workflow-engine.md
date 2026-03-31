# Workflow Engine

## Overview

The workflow engine controls how a `Load` moves through its lifecycle in a predictable, auditable, and enforceable way.

Instead of informal status updates such as spreadsheets or chat messages, the system enforces a state machine that defines:

* what states exist
* which transitions are allowed
* what side effects occur during transitions
* how transitions are recorded

This ensures operational consistency and traceability.

---

## Why a workflow engine is needed

In a manual freight back-office process:

* different people interpret "ready" differently
* loads can jump from incomplete to invoiced incorrectly
* missing documents are overlooked
* no consistent record exists of what happened

The workflow engine solves this by:

* enforcing valid transitions
* centralizing state logic
* recording all transitions as events
* enabling automation triggers

---

## Core components

The workflow system is composed of the following parts.

### 1. LoadStatus (state enum)

Represents the lifecycle states of a load.

Typical states:

* `new`
* `docs_received`
* `extracting`
* `needs_review`
* `validated`
* `ready_to_submit`
* `submitted`
* `funded`
* `paid`
* `exception`
* `archived`

---

### 2. LoadStateMachine

Defines the allowed transitions.

Example:

```text
new -> docs_received
docs_received -> extracting
extracting -> needs_review
needs_review -> validated
validated -> ready_to_submit
ready_to_submit -> submitted
submitted -> funded
funded -> paid
```

Invalid example:

```text
new -> paid
```

The state machine enforces rules such as:

```python
can_transition(current_status, new_status) -> bool
```

---

### 3. LoadTransitionApplier

Applies the transition and handles side effects.

Examples of side effects:

| Transition     | Side effect                         |
| -------------- | ----------------------------------- |
| `-> submitted` | set `submitted_at`                  |
| `-> funded`    | set `funded_at`                     |
| `-> paid`      | set `paid_at`                       |
| `-> validated` | set `processing_status = completed` |
| `-> exception` | set `processing_status = failed`    |

---

### 4. WorkflowEngine

This is the orchestration layer.

Responsibilities:

* validate the transition using the state machine
* apply the transition using the transition applier
* persist the updated load
* create a `WorkflowEvent`

---

### 5. WorkflowEvent

Every transition creates a record.

Example:

```json
{
  "event_type": "status_changed",
  "old_status": "docs_received",
  "new_status": "extracting",
  "actor_type": "system",
  "created_at": "..."
}
```

This enables:

* auditability
* debugging
* timeline reconstruction

---

## Transition flow

Example: document received -> review -> validated

```text
Driver uploads documents
        ↓
Load: new -> docs_received
        ↓
System triggers extraction
        ↓
Load: docs_received -> extracting
        ↓
Extraction completes
        ↓
Load: extracting -> needs_review
        ↓
Staff reviews and fixes data
        ↓
Load: needs_review -> validated
```

---

## Transition validation rules

Each transition must pass:

1. state rule (allowed path)
2. business rule (optional)

Allowed transition:

```python
can_transition("new", "docs_received") == True
```

Blocked transition:

```python
can_transition("new", "paid") == False
```

Business validation examples for a future phase:

* cannot move to `validated` if blocking validation issues exist
* cannot move to `submitted` if required documents are missing
* cannot move to `funded` without a submission timestamp

---

## Processing status vs load status

Two different concepts exist.

### Load status (business lifecycle)

Represents where the load is operationally.

### Processing status (system state)

Typical values:

* `pending`
* `processing`
* `completed`
* `failed`

Examples:

```text
LoadStatus = validated
ProcessingStatus = completed
```

```text
LoadStatus = exception
ProcessingStatus = failed
```

---

## Integration with validation system

The workflow engine interacts with validation.

Flow:

```text
Extraction -> Validation -> Decision
```

If validation issues exist:

```text
-> needs_review
```

If no issues exist:

```text
-> validated
```

Blocking issues prevent forward movement.

---

## Integration with documents

Document events can trigger transitions.

| Event                   | Transition                    |
| ----------------------- | ----------------------------- |
| document uploaded       | `new -> docs_received`        |
| classification complete | `docs_received -> extracting` |
| extraction complete     | `extracting -> needs_review`  |

---

## Integration with billing

Later transitions connect to billing.

| State       | Billing relevance      |
| ----------- | ---------------------- |
| `validated` | ready for invoice      |
| `submitted` | operationally complete |
| `funded`    | payment expected       |
| `paid`      | revenue realized       |

---

## Exception handling

Any step can trigger:

```text
-> exception
```

This is used for:

* validation failure
* system failure
* manual escalation

Effects:

* `processing_status = failed`
* manual intervention is required

---

## Review loop

Loads can cycle through review more than once.

```text
needs_review -> validated -> needs_review
```

Example:

* a reviewer fixes data
* a new validation detects another issue
* the load returns to review

This supports iterative correction.

---

## Auditability

Every transition is recorded with:

* who triggered it
* when it happened
* from status and to status
* optional payload or notes

This allows:

* debugging
* compliance support
* dispute resolution
* analytics

---

## Why this design is important

Without a workflow engine:

* state becomes inconsistent
* logic becomes scattered
* bugs are harder to trace
* automation becomes fragile

With this design:

* transitions are centralized
* rules are enforceable
* behavior is predictable
* future automation becomes easier

---

## Future enhancements

The workflow engine can evolve with the following capabilities.

### 1. Guard conditions

```python
if has_blocking_issues:
    block_transition()
```

### 2. Event-driven triggers

* Kafka or Pub/Sub events
* asynchronous workflows

### 3. SLA tracking

* time spent in each state
* escalation triggers

### 4. Parallel states

* document processing independent of billing

### 5. Retry logic

* failed extraction retry
* webhook retry

---

## Summary

The workflow engine is the control center of load operations.

It helps ensure that:

* loads move correctly
* rules are enforced
* actions are recorded
* automation can be layered safely

It transforms the system from a passive database into an active operational engine.
