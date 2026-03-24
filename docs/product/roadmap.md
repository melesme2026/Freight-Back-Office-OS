Paste this into:

docs/product/roadmap.md

# Product Roadmap

## Purpose

This roadmap defines the phased evolution of Freight Back Office OS from:

- early internal tool (for your uncle’s real workflow)
→ to
- production-grade SaaS platform

This is not just features — it is **business transformation**.

---

## Guiding principles

- Build from **real paperwork and workflows first**
- Prioritize **automation where pain exists**
- Keep system **operator-friendly (not over-engineered UI)**
- Design everything to **scale into SaaS later**
- Replace placeholders only when real data is available

---

## Phase 0 — Foundation (Current Phase)

### Goal
Establish a production-grade backend structure and system architecture.

### Status
✅ In progress (what we are building now)

### Includes

- Full project structure (backend + frontend + infra + docs)
- Domain model (loads, documents, billing, etc.)
- API scaffolding
- Workflow engine
- Validation rules
- Billing system (base)
- Webhook ingestion structure
- Celery worker architecture
- Test scaffolding
- Runbooks and documentation

### Outcome

You now have:
- A real system (not scripts)
- A foundation that can grow
- Something you can plug real data into

---

## Phase 1 — Real Workflow Validation (CRITICAL)

### Goal
Make the system work with **your uncle’s actual paperwork**

### This is the MOST important phase

Without this, nothing else matters.

---

### What you will do

1. Collect real documents:
   - rate confirmations
   - bills of lading
   - invoices

2. Test upload flow:
   - manual upload
   - WhatsApp (later)

3. Validate extraction:
   - identify real fields
   - adjust extraction logic

4. Validate workflow:
   - does load lifecycle match reality?
   - where do things get stuck?

5. Identify gaps:
   - missing fields
   - missing validation rules
   - missing workflow states

---

### System changes expected

- refine extraction_service
- refine validation rules
- refine document classification
- refine workflow transitions

---

### Outcome

- System matches real operations
- No longer “generic software”
- Becomes a **real freight back office tool**

---

## Phase 2 — Automation Layer

### Goal
Reduce manual work

---

### Features

- auto document classification
- auto load matching
- auto extraction improvements
- validation auto-resolution (non-blocking)
- notification automation

---

### Example

Instead of:

> “Check if BOL is missing”

System does:

- detects missing BOL
- sends notification to driver

---

### Outcome

- less manual effort
- faster load processing
- fewer mistakes

---

## Phase 3 — Operator UI (Frontend)

### Goal
Make system usable daily without backend interaction

---

### Key screens

- Dashboard
- Load list
- Load detail view
- Review queue
- Document viewer
- Customer accounts
- Billing dashboard

---

### Driver portal (early version)

- upload documents
- view loads
- see payment status

---

### Outcome

- usable product
- not just backend system
- ready for real usage

---

## Phase 4 — Billing Maturity

### Goal
Turn system into revenue engine

---

### Features

- subscription plans
- usage billing
- invoice automation
- payment tracking
- overdue handling
- reminders

---

### Outcome

- recurring revenue model
- financial visibility
- SaaS-ready billing system

---

## Phase 5 — Multi-Customer / SaaS Mode

### Goal
Support multiple customers (not just your uncle)

---

### Features

- tenant isolation
- role-based access
- API clients
- onboarding automation
- customer dashboards

---

### Outcome

- real SaaS product
- scalable business model

---

## Phase 6 — AI Enhancement

### Goal
Leverage AI for efficiency and accuracy

---

### Features

- improved extraction (LLMs)
- anomaly detection
- smart validation suggestions
- auto-categorization
- support assistant

---

### Outcome

- competitive advantage
- less human effort
- faster processing

---

## Phase 7 — Growth & Platform Expansion

### Goal
Expand beyond core workflow

---

### Possible expansions

- factoring integrations
- dispatch tools
- driver payouts
- analytics dashboards
- integrations (QuickBooks, Stripe, etc.)

---

## Priority order (very important)

Do NOT jump ahead.

Correct order:

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4


⸻

Biggest risk

The biggest failure would be:

building a perfect system that does NOT match real workflow

That’s why:

👉 Phase 1 is the most important phase

⸻

What success looks like

Short term:
	•	your uncle uses it
	•	documents flow through system
	•	loads are tracked correctly

Mid term:
	•	less manual work
	•	fewer errors
	•	faster billing

Long term:
	•	multiple customers
	•	recurring revenue
	•	scalable SaaS platform

⸻

Summary

This roadmap transforms:
	•	manual freight back office work
→ into
	•	automated, structured, scalable system

Step by step.

No shortcuts.

⸻

Next file

docs/product/v1-scope.md