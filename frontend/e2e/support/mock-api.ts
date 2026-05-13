import { Page, Route } from "@playwright/test";
import { seed } from "../fixtures/test-data";

type MockDocument = {
  document_type: string;
  original_filename: string;
};

type MutableState = {
  invoiceCount: number;
  packetCount: number;
  documents: MockDocument[];
  paidAmount: number;
  packetEmailSent: boolean;
};

function ok(route: Route, data: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data }) });
}

function created(route: Route, data: unknown) {
  return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ data }) });
}

function encodeJwtPart(value: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function buildToken(claims: Record<string, unknown>): string {
  return `${encodeJwtPart({ alg: "HS256", typ: "JWT" })}.${encodeJwtPart(claims)}.mock-signature`;
}

function decodeJwtPayload(token: string | null): Record<string, unknown> | null {
  const payload = token?.split(".")[1];
  if (!payload) return null;
  try {
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function authClaims(route: Route): Record<string, unknown> | null {
  const header = route.request().headers().authorization ?? "";
  return decodeJwtPayload(header.replace(/^Bearer\s+/i, ""));
}

const FIXED_ISO_TIMESTAMP = "2026-01-15T12:00:00.000Z";
const LEGACY_MULTI_ORG_DRIVER_ID = "00000000-0000-0000-0000-00000000b222";
const E2E_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 365;

function futureExpiryEpoch(): number {
  return Math.floor(Date.now() / 1000) + E2E_TOKEN_TTL_SECONDS;
}

function carrierProfile() {
  return {
    id: "carrier-profile-e2e-001",
    organization_id: seed.organizationId,
    legal_name: "Adwa Express LLC",
    address_line1: "100 E2E Logistics Way",
    address_line2: "",
    city: "Columbus",
    state: "OH",
    zip: "43215",
    country: "USA",
    phone: "555-0101",
    email: seed.owner.email,
    mc_number: "MC-123456",
    dot_number: "DOT-654321",
    remit_to_name: "Adwa Express LLC",
    remit_to_address: "100 E2E Logistics Way, Columbus, OH 43215",
    remit_to_notes: "ACH preferred for E2E billing packet tests.",
    created_at: FIXED_ISO_TIMESTAMP,
    updated_at: FIXED_ISO_TIMESTAMP,
  };
}

function paymentReconciliation(paidAmountValue = 0) {
  const paidAmount = stateAmountString(paidAmountValue);
  return {
    id: "payment-reconciliation-e2e-001",
    load_id: seed.load.id,
    gross_amount: "1000.00",
    expected_amount: "1000.00",
    amount_received: paidAmount,
    currency: "USD",
    payment_status: paidAmountValue >= 1000 ? "fully_paid" : paidAmountValue > 0 ? "partial" : "open",
    paid_date: paidAmountValue > 0 ? FIXED_ISO_TIMESTAMP : null,
    factoring_used: false,
    factoring_company_id: null,
    factoring_company_name: null,
    factor_name: null,
    factoring_status: null,
    reconciliation_status: "pending",
    aging_bucket: "current",
    advance_amount: null,
    advance_date: null,
    reserve_amount: null,
    reserve_paid_amount: null,
    reserve_pending_amount: null,
    factoring_fee_percent: null,
    factoring_fee_amount: null,
    short_paid_amount: null,
    dispute_reason: null,
    notes: null,
    factoring_notes: null,
  };
}

function stateAmountString(amount: number) {
  return amount.toFixed(2);
}

function mockDocument(documentType: string, originalFilename = `${documentType}.pdf`): MockDocument {
  return { document_type: documentType, original_filename: originalFilename };
}

function presentDocumentTypes(documents: MockDocument[]): string[] {
  return documents.map((document) => document.document_type);
}

function multipartFilename(route: Route): string | null {
  const body = route.request().postData();
  return body?.match(/filename="([^"\r\n]+)"/)?.[1] ?? null;
}

function driverAssignedLoad(status = "in_transit") {
  return {
    ...seed.load,
    id: seed.load.id,
    load_id: seed.load.id,
    load_number: seed.load.load_number,
    organization_id: seed.organizationId,
    driver_id: seed.driver.id,
    driverId: seed.driver.id,
    assigned_driver_id: seed.driver.id,
    driver_name: seed.driver.name,
    status,
    pickup_date: FIXED_ISO_TIMESTAMP,
    delivery_date: FIXED_ISO_TIMESTAMP,
    has_ratecon: true,
    has_bol: true,
    has_pod: false,
    documents_complete: false,
    packet_readiness: {
      readiness_state: "missing_required_documents",
      ready_for_invoice: false,
      ready_to_submit: false,
      present_documents: ["rate_confirmation", "bill_of_lading"],
      missing_required_documents: { invoice: [], submission: ["proof_of_delivery"] },
      blockers: ["proof_of_delivery"],
      notes: ["Proof of Delivery is required before submission."],
    },
  };
}

export async function mockApi(page: Page) {
  const state: MutableState = {
    invoiceCount: 0,
    packetCount: 0,
    documents: [mockDocument("rate_confirmation"), mockDocument("bill_of_lading")],
    paidAmount: 0,
    packetEmailSent: false,
  };

  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace("/api/v1", "");
    const method = req.method();

    if (path === "/auth/login" && method === "POST") {
      const body = req.postDataJSON() as { email?: string; password?: string; organization_id?: string };
      if (body?.password !== seed.owner.password) {
        return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { message: "Invalid credentials" } }) });
      }
      if (body?.email === "multi@example.com" && !body.organization_id) {
        return route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "multiple_organizations",
              message: "This email is linked to multiple workspaces. Select the workspace you want to access.",
              details: {
                organizations: [
                  { organization_id: "00000000-0000-0000-0000-00000000a111", organization_name: "Adwa Express LLC", role: "owner" },
                  { organization_id: seed.organizationId, organization_name: "Adwa Driver Ops", role: "driver" },
                ],
              },
            },
          }),
        });
      }
      if (body?.email === "multi@example.com" && body.organization_id === "00000000-0000-0000-0000-00000000c333") {
        return route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "invalid_organization_selection",
              message: "Invalid workspace selection.",
            },
          }),
        });
      }
      const role = body.email === seed.driver.email || body.organization_id === seed.organizationId || body.organization_id === LEGACY_MULTI_ORG_DRIVER_ID ? "driver" : "owner";
      const organizationId = role === "driver" ? seed.organizationId : body.organization_id ?? seed.organizationId;
      const email = role === "driver" ? seed.driver.email : body?.email ?? seed.owner.email;
      const accessToken = buildToken({
        sub: email,
        email,
        exp: futureExpiryEpoch(),
        role,
        organization_id: organizationId,
        ...(role === "driver" ? { driver_id: seed.driver.id } : {}),
      });
      return ok(route, {
        access_token: accessToken,
        token_type: "Bearer",
        user: {
          email,
          role,
          organization_id: organizationId,
          ...(role === "driver" ? { driver_id: seed.driver.id } : {}),
        },
      });
    }

    if (path === "/auth/signup" && method === "POST") {
      const body = req.postDataJSON() as { email?: string; organization_name?: string };
      if ((body?.organization_name ?? "").toLowerCase().includes("duplicate")) {
        return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: { message: "Organization already exists" } }) });
      }
      const accessToken = buildToken({
        sub: body?.email ?? "owner.e2e@example.com",
        exp: futureExpiryEpoch(),
        role: "owner",
        organization_id: seed.organizationId,
      });
      return created(route, { access_token: accessToken, token_type: "Bearer", user: { role: "owner", organization_id: seed.organizationId, email: body.email } });
    }

    if (path === `/drivers/${seed.driver.id}` && method === "GET") {
      return ok(route, {
        id: seed.driver.id,
        full_name: seed.driver.name,
        email: seed.driver.email,
        phone: "555-0100",
        is_active: true,
        status: "active",
      });
    }

    if (path.startsWith("/drivers") && method === "GET") {
      return ok(route, [{ id: seed.driver.id, full_name: seed.driver.name, email: seed.driver.email, is_active: true }]);
    }

    if (path.startsWith("/brokers") && method === "GET") {
      return ok(route, [{ id: seed.broker.id, organization_id: seed.organizationId, name: seed.broker.name, email: seed.broker.email }]);
    }

    if (path.startsWith("/customer-accounts") && method === "GET") {
      return ok(route, [{ id: seed.customer.id, account_name: seed.customer.account_name, status: "active" }]);
    }

    if (path.startsWith("/operations/command-center") && method === "GET") {
      return ok(route, {
        generated_at: FIXED_ISO_TIMESTAMP,
        kpis: {
          active_loads: 1,
          loads_missing_docs: 0,
          overdue_invoices: 0,
          urgent_collections: 0,
          pending_packet_sends: state.packetCount > 0 && !state.packetEmailSent ? 1 : 0,
          unresolved_packet_intelligence_blockers: 0,
          factoring_reserve_pending: 0,
          unpaid_total: stateAmountString(Math.max(0, 1000 - state.paidAmount)),
          factoring_reserve_pending_total: "0.00",
        },
        alerts: [],
        missing_docs: {
          summary: {
            total_loads: 0,
            blocked_from_packet_send: 0,
            by_document_type: {},
            critical_count: 0,
            warning_count: 0,
          },
          items: [],
        },
        collections: {
          summary: {
            total_unpaid_items: state.paidAmount >= 1000 ? 0 : 1,
            urgent_count: 0,
            overdue_count: 0,
            unpaid_total: stateAmountString(Math.max(0, 1000 - state.paidAmount)),
            reserve_pending_total: "0.00",
          },
          items: [],
        },
        tasks: {
          summary: { total: 0, critical: 0, warning: 0, info: 0 },
          items: [],
        },
        ai_operations_assistant: {
          summary: [],
          invoice_risks: [],
          broker_insights: [],
          collections_priorities: [],
          recommendations: [],
          explainability: {
            mode: "deterministic_rules_only",
            uses_llm: false,
            autonomous_actions: false,
            rules: ["E2E mock returns deterministic command center data."],
          },
        },
        broker_behavior: {
          summary: {
            broker_count: 1,
            worsening_count: 0,
            dispute_or_short_paid_count: 0,
            unpaid_total: stateAmountString(Math.max(0, 1000 - state.paidAmount)),
            reserve_pending_total: "0.00",
          },
          items: [],
        },
        priority_cards: [],
        recent_activity: [],
        meta: {
          load_limit: 50,
          payment_limit: 50,
          logic: "e2e_mock",
          ai_assistant_logic: "deterministic_rules_only",
          not_implemented: [],
        },
      });
    }

    if (path.startsWith("/dashboard") && method === "GET") {
      return ok(route, {
        loads_total: 1,
        loads_needing_review: 0,
        loads_validated: 1,
        loads_ready_to_submit: 1,
        loads_submitted_to_broker: 0,
        loads_waiting_on_broker: 0,
        loads_submitted_to_factoring: 0,
        loads_waiting_on_funding: 0,
        loads_funded: 0,
        loads_paid: 0,
        documents_pending_processing: 0,
        critical_validation_issues: 0,
        operational_queues: { invoice_ready: 1 },
        queue_load_examples: {},
      });
    }

    if (path.startsWith("/onboarding/") && method === "GET") {
      return ok(route, {
        id: "onb-e2e-001",
        customer_account_id: seed.customer.id,
        status: "in_progress",
        documents_received: true,
        pricing_confirmed: true,
        payment_method_added: false,
        driver_profiles_created: true,
        channel_connected: false,
        go_live_ready: false,
        completed_at: null,
        updated_at: FIXED_ISO_TIMESTAMP,
      });
    }

    if (path === "/auth/me" && method === "GET") {
      const claims = authClaims(route);
      const role = typeof claims?.role === "string" ? claims.role : "owner";
      const organizationId = role === "driver" ? seed.organizationId : typeof claims?.organization_id === "string" ? claims.organization_id : seed.organizationId;
      const email = role === "driver" ? seed.driver.email : typeof claims?.email === "string" ? claims.email : seed.owner.email;
      return ok(route, {
        id: role === "driver" ? seed.driver.id : "staff-e2e-001",
        email,
        role,
        organization_id: organizationId,
        ...(role === "driver" ? { driver_id: seed.driver.id, assigned_driver_id: seed.driver.id } : {}),
      });
    }

    if (path === "/auth/invite-user" && method === "POST") {
      return ok(route, {
        email_status: "disabled",
        activation_url: "/activate-account?token=manual-token-e2e",
      });
    }

    if (path === "/auth/activate-account" && method === "POST") {
      return ok(route, { activated: true });
    }

    if (path.startsWith("/staff-users") && method === "GET") {
      return ok(route, [{ id: "staff-e2e-001", full_name: "Owner E2E" }]);
    }

    if (path.includes("/review-queue/loads/") && path.endsWith("/context") && method === "GET") {
      return ok(route, {
        id: "rq-e2e-001",
        load_id: seed.load.id,
        can_generate_invoice: true,
        can_create_packet: true,
      });
    }

    if (path === "/documents" && method === "GET") {
      return ok(route, state.documents.map((doc, index) => ({
        id: `driver-doc-${index + 1}`,
        load_id: seed.load.id,
        load_number: seed.load.load_number,
        file_name: doc.original_filename,
        original_filename: doc.original_filename,
        document_type: doc.document_type,
        processing_status: "accepted",
        received_at: FIXED_ISO_TIMESTAMP,
      })));
    }

    if (path.includes("/loads/") && path.endsWith("/documents") && method === "GET") {
      return ok(route, state.documents.map((doc, index) => ({ id: `doc-${index + 1}`, file_name: doc.original_filename, document_type: doc.document_type })));
    }

    if (path.includes("/payment-reconciliation") && method === "GET") {
      return ok(route, { expected_amount: 1000, amount_received: state.paidAmount, reserve_amount: 0, reserve_paid_amount: 0 });
    }

    if (path.includes("/payment-reconciliation") && ["POST", "PATCH"].includes(method)) {
      const body = req.postDataJSON() as { amount?: string | number; amount_received?: string | number } | null;
      const amount = Number(body?.amount_received ?? body?.amount ?? 0);
      if (Number.isFinite(amount) && amount > 0) {
        state.paidAmount = Math.min(1000, state.paidAmount + amount);
      }
      return ok(route, { expected_amount: 1000, amount_received: state.paidAmount, reserve_amount: 0, reserve_paid_amount: 0 });
    }

    if (path.startsWith("/follow-ups") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/support/tickets") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/follow-ups/") && method === "POST") {
      return ok(route, { id: "fup-1", status: "open" });
    }

    if (path.includes("/follow-ups/generate") && method === "POST") {
      return ok(route, []);
    }

    if (path === "/carrier-profile" && method === "GET") {
      return ok(route, { legal_name: "Freight Back Office Carrier", mc_number: "MC-12345", dot_number: "DOT-12345" });
    }

    if (path === "/carrier-profile" && ["POST", "PUT", "PATCH"].includes(method)) {
      const body = req.postDataJSON() as Record<string, unknown> | null;
      return ok(route, body ?? {});
    }

    if (path === `/loads/${seed.load.id}/invoice` && method === "GET") {
      if (state.invoiceCount === 0) {
        state.invoiceCount += 1;
      }
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: {
          "content-disposition": 'attachment; filename="invoice-INV-E2E-001.pdf"',
        },
        body: "%PDF-1.4 mock-invoice",
      });
    }

    if (path.startsWith("/loads") && method === "GET" && !path.includes("driver")) {
      if (path === `/loads/${seed.load.id}`) {
        return ok(route, {
          ...seed.load,
          id: seed.load.id,
          status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready",
          driver_id: seed.driver.id,
          driver_name: seed.driver.name,
          broker_id: seed.broker.id,
          broker_name: seed.broker.name,
          customer_account_id: seed.customer.id,
          customer_account_name: seed.customer.account_name,
          gross_amount: 1000,
          packet_readiness: {
            ready_for_invoice: true,
            ready_to_submit: true,
            missing_required_documents: { submission: [], invoice: [] },
            present_documents: presentDocumentTypes(state.documents),
          },
          amount_received: state.paidAmount,
          has_invoice: state.invoiceCount > 0,
          invoice_number: state.invoiceCount > 0 ? "INV-E2E-001" : null,
        });
      }
      return ok(route, [{ ...seed.load, status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready", driver_name: seed.driver.name }]);
    }

    if (path === "/documents/upload" && method === "POST") {
      state.documents.push(mockDocument("support"));
      return created(route, { id: `doc-${state.documents.length}` });
    }

    if (path === "/driver/documents/upload" && method === "POST") {
      const originalFilename = multipartFilename(route) ?? "pod-photo.png";
      state.documents.push(mockDocument("proof_of_delivery", originalFilename));
      return created(route, {
        id: `doc-driver-${state.documents.length}`,
        load_id: seed.load.id,
        load_number: seed.load.load_number,
        original_filename: originalFilename,
        document_type: "proof_of_delivery",
        processing_status: "accepted",
        received_at: FIXED_ISO_TIMESTAMP,
      });
    }

    if (path.includes("/generate-invoice") && method === "POST") {
      if (state.invoiceCount === 0) {
        state.invoiceCount += 1;
      }
      return created(route, { id: "inv-e2e-001", invoice_number: "INV-E2E-001" });
    }

    if (path.includes("/send-email") && method === "POST") {
      state.packetEmailSent = true;
      return ok(route, { status: "queued", message: "Packet email sent and logged" });
    }

    if (path.includes("/submission-packets") && method === "POST") {
      state.packetCount += 1;
      state.packetEmailSent = false;
      return created(route, { id: `packet-${state.packetCount}`, packet_reference: "PKT-E2E-1", status: "created", destination_email: "ap@broker.test", documents: [{ id: "d1", document_type: "invoice" }], events: [{ id: "e1", event_type: "created", message: "Packet created", created_at: FIXED_ISO_TIMESTAMP }] });
    }

    if (path.includes("/submission-packets") && method === "GET") {
      const packetEvents = [
        ...(state.packetEmailSent ? [{ id: "e2", event_type: "packet_email_sent", message: "Packet email sent and logged", created_at: FIXED_ISO_TIMESTAMP, recipient: "ap@broker.test" }] : []),
        { id: "e1", event_type: "created", message: "Packet created", created_at: FIXED_ISO_TIMESTAMP },
      ];
      const packets = state.packetCount > 0 ? [{ id: "packet-1", packet_reference: "PKT-E2E-1", status: state.packetEmailSent ? "sent" : "created", sent_at: state.packetEmailSent ? FIXED_ISO_TIMESTAMP : null, destination_email: "ap@broker.test", documents: [{ id: "d1", document_type: "invoice" }], events: packetEvents }] : [];
      return ok(route, packets);
    }

    if (path.includes("/submission-packets/") && path.endsWith("/download") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/zip", body: "PK\x03\x04" });
    }

    if (path === "/carrier-profile" && method === "GET") {
      return ok(route, carrierProfile());
    }

    if (path === "/carrier-profile" && (method === "POST" || method === "PATCH")) {
      const body = req.postDataJSON() as Record<string, unknown> | null;
      return ok(route, { ...carrierProfile(), ...(body ?? {}), updated_at: FIXED_ISO_TIMESTAMP });
    }

    if (path.includes("/loads/") && path.endsWith("/packet-audit") && method === "GET") {
      return ok(route, { status: "passed", findings: [] });
    }

    if (path.includes("/loads/") && path.endsWith("/payment-reconciliation/") && method === "GET") {
      return ok(route, paymentReconciliation(state.paidAmount));
    }

    if (path.includes("/loads/") && path.includes("/payment-reconciliation") && (method === "POST" || method === "PATCH")) {
      const body = req.postDataJSON() as Record<string, unknown> | null;
      return ok(route, { ...paymentReconciliation(state.paidAmount), ...(body ?? {}) });
    }

    if (path.startsWith("/follow-ups") && method === "GET") {
      return ok(route, []);
    }

    if (path.includes("/loads/") && path.endsWith("/follow-ups/generate") && method === "POST") {
      return ok(route, { created_count: 0, tasks: [] });
    }

    if (path.startsWith("/follow-ups/") && method === "POST") {
      return ok(route, { id: "follow-up-e2e-001", status: "completed" });
    }

    if (path.includes("/loads/") && path.endsWith("/status") && method === "POST") {
      return ok(route, { new_status: "invoice_ready" });
    }

    if (path.includes("/driver/loads/") && path.endsWith("/check-in") && method === "POST") {
      return ok(route, driverAssignedLoad("in_transit"));
    }

    if (path.includes("/workflow-actions") && method === "POST") {
      return ok(route, { new_status: "invoice_ready" });
    }

    if (path.includes("/payments") && method === "POST") {
      const body = req.postDataJSON() as { amount_received?: string | number };
      const amount = Number(body?.amount_received ?? 0);
      if (!Number.isFinite(amount) || amount <= 0) {
        return route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ error: { message: "Invalid amount" } }) });
      }
      state.paidAmount += amount;
      return created(route, { id: `pay-${state.paidAmount}`, amount_received: amount });
    }

    if (path.startsWith("/payments") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/driver/loads") && method === "GET") {
      const assignedDriverLoad = driverAssignedLoad();
      if (path === `/driver/loads/${seed.load.id}`) {
        return ok(route, assignedDriverLoad);
      }
      return ok(route, [assignedDriverLoad]);
    }

    if (path.startsWith("/reports/money-dashboard") && method === "GET") {
      return ok(route, {
        summary: { total_receivables: 1000, total_outstanding: Math.max(0, 1000 - state.paidAmount), total_received: state.paidAmount, overdue_amount: 0, reserve_pending_amount: 0, disputed_count: 0, short_paid_count: 0 },
        aging_buckets: [],
        status_breakdown: [{ status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready", count: 1, amount: 1000 }],
        factoring_vs_direct: { factored: { count: 0, amount: 0 }, direct: { count: 1, amount: 1000 }, advance_total: 0, reserve_pending_total: 0, direct_unpaid_total: Math.max(0, 1000 - state.paidAmount) },
        needs_attention: { urgent_count: 0, overdue_followups_count: 0, top_items: [] },
        recent_cash_activity: [{ load_number: seed.load.load_number, amount_received: state.paidAmount, paid_date: FIXED_ISO_TIMESTAMP, payment_status: state.paidAmount >= 1000 ? "fully_paid" : "partial", factoring_used: false }],
      });
    }

    if (path.startsWith("/billing/dashboard") && method === "GET") {
      return ok(route, { active_subscriptions: 0, open_invoices: 0, past_due_invoices: 0, collected_this_month: 0, currency_code: "USD" });
    }

    if (path.startsWith("/billing/invoices") && method === "GET") {
      return ok(route, { items: state.invoiceCount > 0 ? [{ id: "inv-e2e-001", invoice_number: "INV-E2E-001", status: "open", total_amount: 1000, currency_code: "USD", customer_account_id: seed.customer.id }] : [] });
    }

    if (path.startsWith("/billing-invoices") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/subscriptions") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/organization/billing") && method === "GET") {
      return ok(route, { id: seed.organizationId, billing_provider: "stripe", billing_status: "trial", plan_code: "starter" });
    }

    if (path.startsWith("/organization/billing") && method === "PATCH") {
      return ok(route, { id: seed.organizationId, billing_provider: "stripe", billing_status: "trial", plan_code: "starter" });
    }

    return route.fulfill({
      status: 501,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          message: `E2E mock missing handler for ${method} ${path}`,
        },
      }),
    });
  });
}
