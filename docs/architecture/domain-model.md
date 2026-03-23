# Domain Model

## Overview

Freight Back Office OS is modeled as a set of business domains that represent how a freight back office actually operates. The model is intentionally explicit so that each operational concern has a stable place in the system.

The domain is organized around six major areas:

- tenant and identity
- commercial accounts and onboarding
- freight operations
- documents, extraction, and validation
- billing and financial operations
- support, notifications, and auditability

## Domain principles

The model follows these principles:

- each business concept should map to a distinct entity
- core workflow entities should be auditable
- operational events should be explicit, not implicit
- billing should be separate from load execution but still linkable
- document processing should support both automation and human correction
- the structure should work for a small operator today and a SaaS product later

---

## 1. Tenant and identity domain

### Organization

`Organization` is the tenant boundary.

It represents the company, operating entity, or back-office business using the platform. Almost all major records belong to an organization.

Typical responsibilities:

- own customer accounts
- own drivers and brokers
- own loads and documents
- own billing plans and subscriptions
- scope access and reporting

### StaffUser

`StaffUser` represents an internal operator, dispatcher, reviewer, admin, or finance user working inside the system.

Typical responsibilities:

- perform reviews
- transition loads
- manage onboarding
- create support tickets
- correct extracted fields
- resolve validation issues

### ApiClient

`ApiClient` represents a machine credential for system-to-system access.

Typical responsibilities:

- authenticated external integrations
- internal automation access
- webhook or API consumer identity
- scoped machine actions

---

## 2. Commercial account and onboarding domain

### CustomerAccount

`CustomerAccount` represents the customer or client relationship the platform is serving.

This is one of the central business records in the system.

Typical attributes:

- account name
- account code
- billing email
- primary contact info
- account status
- notes

Typical relationships:

- one organization has many customer accounts
- one customer account can have many drivers
- one customer account can have many loads
- one customer account can have one onboarding checklist
- one customer account can have many subscriptions, invoices, payments, support tickets, and referrals

### OnboardingChecklist

`OnboardingChecklist` represents customer go-live readiness.

It tracks whether a customer is operationally ready to use the service.

Typical steps:

- documents received
- pricing confirmed
- payment method added
- driver profiles created
- channel connected
- go-live ready

This is intentionally modeled as a structured entity rather than a generic notes field because onboarding is a repeatable process.

### Referral

`Referral` represents a lead or referral source related to a customer account or prospect flow.

Typical use cases:

- track who referred the account
- support marketing attribution later
- support incentives or partner tracking
- retain commercial context around account origin

---

## 3. Freight operations domain

### Driver

`Driver` represents a driver profile.

A driver may belong to a customer account and will often be associated with document intake and load activity.

Typical attributes:

- full name
- phone
- email
- active flag

Typical responsibilities:

- source of WhatsApp or upload documents
- associated with loads
- may receive notifications
- may be tied to support tickets or payments

### Broker

`Broker` represents the freight broker or commercial counterparty on the load side.

Typical attributes:

- broker name
- MC number
- contact details
- payment terms
- notes

This allows broker data to evolve from raw text into reusable master data.

### Load

`Load` is the core operational entity.

A load represents one shipment workflow moving through the back office.

This is the most important operational record in the system.

Typical attributes:

- load number
- rate confirmation number
- BOL number
- invoice number
- pickup and delivery dates
- pickup and delivery locations
- gross amount
- currency
- source channel
- workflow status
- processing status
- completeness flags

Typical flags:

- has rate confirmation
- has BOL
- has invoice
- documents complete

Typical lifecycle states:

- new
- docs received
- extracting
- needs review
- validated
- ready to submit
- submitted
- funded
- paid
- exception
- archived

Typical relationships:

- one load belongs to one organization
- one load belongs to one customer account
- one load belongs to one driver
- one load may belong to one broker
- one load may have many documents
- one load may have many extracted fields
- one load may have many validation issues
- one load may have many workflow events
- one load may have many notifications
- one load may have many support tickets
- one load may have many usage records

### WorkflowEvent

`WorkflowEvent` records an operational event related to a load.

This exists so workflow history is explicit and auditable.

Typical examples:

- status changed
- review completed
- exception raised
- document linked
- reconciliation action
- submission recorded

A workflow event usually stores:

- event type
- old status
- new status
- actor type
- actor user if applicable
- payload or notes

This makes the load timeline inspectable.

---

## 4. Documents, extraction, and validation domain

### LoadDocument

`LoadDocument` represents a file received by the system.

Examples:

- rate confirmation PDF
- bill of lading image
- proof of delivery photo
- invoice PDF
- unknown attachment

Typical attributes:

- original filename
- mime type
- file hash
- storage location
- document type
- processing status
- page count
- received timestamp
- source channel
- classification confidence

Typical relationships:

- belongs to organization
- belongs to customer account
- may belong to driver
- may belong to load
- may be uploaded by a staff user
- has many extracted fields
- may have many validation issues

### ExtractedField

`ExtractedField` represents one structured value derived from a document.

Examples:

- invoice amount
- broker name
- broker email
- document type
- pickup date
- load number
- signature present

Typical attributes:

- field name
- text value
- numeric value
- date value
- JSON value
- confidence score
- source model
- source engine
- human-corrected flag
- corrected by
- corrected at

This supports both automated extraction and human review.

### ValidationIssue

`ValidationIssue` represents a business rule problem identified during document or load validation.

Examples:

- missing signature
- amount mismatch
- duplicate load
- unreadable document
- missing required fields
- broker mismatch

Typical attributes:

- rule code
- severity
- title
- description
- blocking flag
- resolved flag
- resolved by
- resolution notes

Validation issues are not just logs. They are actionable operational work items.

---

## 5. Billing and financial operations domain

### ServicePlan

`ServicePlan` represents a commercial pricing plan offered by the platform.

Typical attributes:

- plan name
- plan code
- billing cycle
- base price
- per-load price
- per-driver price
- active flag

Examples:

- starter monthly plan
- growth plan
- enterprise plan
- hybrid base plus usage plan

### Subscription

`Subscription` represents a customer account’s enrollment in a service plan.

Typical attributes:

- service plan
- current status
- billing period start/end
- cancel at period end
- billing email
- notes

Typical relationships:

- belongs to customer account
- belongs to service plan
- may have many usage records
- may have many invoices

### UsageRecord

`UsageRecord` captures billable or measurable activity tied to a subscription.

Examples:

- per load usage
- per driver usage
- add-on billing
- premium workflow volume

Typical attributes:

- usage type
- quantity
- unit price
- usage date
- metadata

It allows the system to support usage-based billing in addition to flat pricing.

### BillingInvoice

`BillingInvoice` represents an issued invoice to a customer account.

Typical attributes:

- invoice number
- status
- subtotal
- tax
- total
- amount paid
- amount due
- issued at
- due at
- paid at
- billing period start/end
- notes

Typical relationships:

- belongs to customer account
- may belong to subscription
- has many invoice lines
- has many payments
- has many ledger entries

### BillingInvoiceLine

`BillingInvoiceLine` represents a single invoice line item.

Examples:

- monthly platform fee
- per-load charge
- per-driver charge
- adjustment
- manual fee

Typical attributes:

- line type
- description
- quantity
- unit price
- line total
- metadata
- optional usage record linkage

### PaymentMethod

`PaymentMethod` represents a saved payment instrument for a customer account.

Typical attributes:

- provider
- provider customer ID
- provider payment method ID
- method type
- brand
- last4
- expiration values
- default flag
- active flag

### Payment

`Payment` represents a payment attempt or collected payment.

Typical attributes:

- provider
- status
- amount
- currency
- attempted at
- succeeded at
- failed at
- failure reason
- metadata

Typical relationships:

- belongs to customer account
- may belong to invoice
- may belong to payment method
- may belong to driver
- may be recorded by staff user
- may have ledger entries

### LedgerEntry

`LedgerEntry` represents an accounting-style financial record.

Examples:

- invoice posted
- payment received
- adjustment
- write-off
- credit
- debit

It is the audit-friendly financial trail behind invoices and payments.

---

## 6. Support, notifications, and audit domain

### Notification

`Notification` represents a communication record.

Examples:

- outbound WhatsApp status update
- outbound email notice
- internal notification
- delivery status tracking

Typical attributes:

- channel
- direction
- message type
- subject
- body
- provider message ID
- send/delivery/failure timestamps
- error message

This enables unified communication history across channels.

### SupportTicket

`SupportTicket` represents an operational or customer support issue.

Examples:

- missing document question
- billing problem
- driver issue
- workflow exception investigation
- onboarding blocker

Typical attributes:

- subject
- description
- status
- priority
- assigned staff user
- resolved timestamp

Tickets may link to:

- customer account
- driver
- load

### AuditLog

`AuditLog` records important auditable actions across the system.

Examples:

- subscription updated
- invoice status changed
- customer account modified
- workflow action performed
- support ticket updated
- role or permission-sensitive events

Typical attributes:

- actor type
- actor ID
- entity type
- entity ID
- action
- changes JSON
- metadata JSON

Audit logs are system-level accountability records.

---

## Relationship summary

Below is the conceptual relationship map.

### Organization owns

- customer accounts
- staff users
- drivers
- brokers
- loads
- documents
- validation issues
- workflow events
- notifications
- service plans
- subscriptions
- invoices
- payment methods
- payments
- ledger entries
- support tickets
- audit logs
- api clients

### CustomerAccount connects to

- onboarding checklist
- referrals
- drivers
- loads
- subscriptions
- invoices
- payment methods
- payments
- ledger entries
- support tickets
- notifications
- usage records

### Load connects to

- driver
- broker
- customer account
- documents
- extracted fields
- validation issues
- workflow events
- support tickets
- notifications
- usage records

### Billing connects to operations through

- customer account
- subscription
- usage record
- load
- driver

This keeps billing linked to real operations without making the load entity itself responsible for invoicing behavior.

---

## Why this model works

This domain model works because it separates concerns clearly:

- **operations** are centered on loads
- **documents** are centered on intake, extraction, and validation
- **commercial management** is centered on customer accounts and onboarding
- **billing** is centered on plans, subscriptions, invoices, payments, and usage
- **support and accountability** are centered on notifications, tickets, and audit logs

That means the system can evolve safely without collapsing unrelated concerns into one overloaded entity.

## Future domain expansion

As the platform matures, likely future additions include:

- dispatch assignments
- carrier compliance records
- factoring integrations
- customer contract terms
- payout tracking to drivers
- role-based authorization model
- SLA tracking
- document versioning
- reconciliation batches
- analytics fact tables
- AI review feedback loops

## Summary

The domain model of Freight Back Office OS is designed to reflect real freight back-office work while staying modular enough for long-term productization.

At the center of the model is the load, but the real strength of the system comes from the surrounding domains that make the load operationally complete:

- documents
- validation
- workflow
- onboarding
- billing
- support
- audit