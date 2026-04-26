# Pilot Onboarding Guide

This guide is for the first real pilot users of Freight Back Office OS.

## Operating modes

- **Demo / local mode:** for local development and workflow learning. Seed data is allowed.
- **Pilot mode:** real carrier/broker/customer/driver records in a controlled environment with restricted team access.
- **Production mode:** hardened deployment with full environment validation, observability, backups, and billing integrations configured.

## Production environment requirements

Before broad production rollout, validate at minimum:

1. API/Web/Worker deployment health checks pass.
2. Organization-scoped auth/RBAC is enforced for all pilot users.
3. Document storage, backups, and retention policies are configured.
4. Notification channels (email/WhatsApp where applicable) are validated.
5. Billing configuration is explicit; if subscription checkout is incomplete, communicate that it is not fully enabled.

## First carrier setup

1. Sign in as Owner or Admin.
2. Open **Dashboard → Settings → Carrier Profile**.
3. Fill legal/business identity details and contact channels.
4. Save and verify profile data appears in invoice and packet workflows.

## First driver setup

1. Open **Dashboard → Drivers**.
2. Select **Add Driver**.
3. Enter full name and contact details.
4. Confirm driver is visible in the Drivers list.

## First load workflow

1. Open **Dashboard → Loads**.
2. Select **New Load** and enter route, broker, customer, and financial details.
3. Assign a driver.
4. Save and verify status appears in the Loads list.

## First invoice workflow

1. Open the load detail page.
2. Upload required documents (rate confirmation, BOL/POD as needed).
3. Generate invoice from the load workflow.
4. Verify invoice appears under **Dashboard → Billing → Invoices**.

## First packet send

1. From load detail, create a submission packet.
2. Review included documents and invoice.
3. Mark packet as sent after external delivery.
4. Confirm packet status updates on the load timeline.

## First payment tracking

1. Open **Dashboard → Money Dashboard**.
2. Record payment state updates through the billing/payment workflow.
3. Verify status, overdue, and received totals update.
4. Use **Follow-Ups** for overdue or reserve-pending actions.

## Troubleshooting

- **No data visible:** verify organization context and user role.
- **Cannot access money or billing sections:** confirm user is not in driver-only scope.
- **Checklist appears incomplete:** verify each workflow step is saved successfully (driver, load, docs, invoice, packet, payment).
- **Subscription checkout unavailable:** configure Stripe checkout environment variables and redeploy frontend.
- **Unexpected API errors:** run launch smoke tests and inspect API/worker logs before pilot go-live.
