import { Page, Route } from "@playwright/test";
import { seed } from "../fixtures/test-data";

type MutableState = {
  invoiceCount: number;
  packetCount: number;
  documents: string[];
  paidAmount: number;
  portalDocuments: string[];
};

function ok(route: Route, data: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data }) });
}

function created(route: Route, data: unknown) {
  return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ data }) });
}


function error(route: Route, status: number, message: string, code?: string) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({ error: { code, message } }),
  });
}

function portalScope() {
  return {
    load_id: seed.load.id,
    role: "broker",
    contact_email: seed.broker.email,
    contact_name: seed.broker.name,
    allow_packet_download: true,
    allow_document_upload: true,
  };
}

function portalLoad() {
  return {
    ...seed.load,
    status: "invoice_ready",
    pickup_date: "2026-05-01",
    delivery_date: "2026-05-02",
    broker_name: seed.broker.name,
    customer_account_name: seed.customer.account_name,
    rate_confirmation_number: "RC-E2E-001",
    bol_number: "BOL-E2E-001",
    invoice_number: "INV-E2E-001",
    documents_complete: true,
    has_ratecon: true,
    has_bol: true,
    has_invoice: true,
    packet_readiness: {
      ready: true,
      missing_documents: [],
      present_documents: ["rate_confirmation", "proof_of_delivery", "invoice"],
      required_documents: ["rate_confirmation", "proof_of_delivery", "invoice"],
    },
    submitted_at: null,
    paid_at: null,
    updated_at: "2026-05-09T00:00:00.000Z",
  };
}

function analyticsResponse() {
  return {
    filters: { date_from: null, date_to: null, broker_id: null, driver_id: null, factoring_status: null },
    metric_definitions: { total_revenue: "Gross load revenue in the selected period." },
    revenue: {
      total_revenue: "1000.00",
      paid_revenue: "0.00",
      received_revenue: "0.00",
      unpaid_revenue: "1000.00",
      factored_revenue: "0.00",
      invoice_count: 1,
      average_invoice_amount: "1000.00",
      monthly_trends: [{ month: "2026-05", revenue: "1000.00", paid_revenue: "0.00", unpaid_revenue: "1000.00", invoice_count: 1 }],
    },
    unpaid_invoices: { unpaid_count: 1, partially_paid_count: 0, overdue_count: 0, unpaid_total: "1000.00", partially_paid_total: "0.00", overdue_total: "0.00", items: [] },
    aging_report: { buckets: [{ bucket: "0_30", label: "0-30 days", count: 1, balance: "1000.00" }], total_count: 1, total_balance: "1000.00" },
    driver_profitability: [],
    broker_performance: [],
    lane_profitability: [],
    collections: {
      unpaid_total: "1000.00",
      overdue_balance: "0.00",
      reserve_pending_total: "0.00",
      unreconciled_count: 0,
      unreconciled_balance: "0.00",
      dispute_count: 0,
      short_paid_count: 0,
      risk_summary: { high_risk_count: 0, high_risk_balance: "0.00", medium_risk_count: 0, medium_risk_balance: "0.00", low_risk_count: 1, low_risk_balance: "1000.00" },
      oldest_invoices: [],
    },
    filter_options: { brokers: [{ id: seed.broker.id, name: seed.broker.name }], drivers: [{ id: seed.driver.id, name: seed.driver.name }], factoring_statuses: ["not_factored"] },
  };
}

function commandCenterResponse() {
  return {
    kpis: { active_loads: 1, loads_missing_docs: 0, overdue_invoices: 0, urgent_collections: 0, pending_packet_sends: 1, unresolved_packet_intelligence_blockers: 0, factoring_reserve_pending: 0, unpaid_total: "1000.00", factoring_reserve_pending_total: "0.00" },
    alerts: [],
    missing_docs: { summary: { count: 0 }, items: [] },
    collections: { summary: { count: 0 }, items: [] },
    packet_intelligence: { summary: { count: 0 }, items: [] },
    factoring: { summary: { count: 0 }, items: [] },
    task_center: { summary: { count: 0 }, items: [] },
    broker_behavior: { summary: { broker_count: 1, worsening_count: 0, dispute_or_short_paid_count: 0, unpaid_total: "1000.00", reserve_pending_total: "0.00" }, items: [] },
    priority_cards: [],
    recent_activity: [],
    meta: { load_limit: 10, payment_limit: 10, logic: "e2e deterministic fixture", not_implemented: [] },
  };
}

function encodeJwtPart(value: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function buildToken(claims: Record<string, unknown>): string {
  return `${encodeJwtPart({ alg: "HS256", typ: "JWT" })}.${encodeJwtPart(claims)}.mock-signature`;
}

export async function mockApi(page: Page) {
  const state: MutableState = {
    invoiceCount: 0,
    packetCount: 0,
    documents: ["rate_confirmation", "bill_of_lading", "proof_of_delivery"],
    paidAmount: 0,
    portalDocuments: ["rate_confirmation", "proof_of_delivery"],
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
                  { organization_id: "00000000-0000-0000-0000-00000000b222", organization_name: "Adwa Driver Ops", role: "driver" },
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
      const role = body.email === seed.driver.email || body.organization_id === "00000000-0000-0000-0000-00000000b222" ? "driver" : "owner";
      const organizationId = body.organization_id ?? seed.organizationId;
      const expiresAtEpoch = Math.floor(Date.now() / 1000) + 60 * 60;
      const accessToken = buildToken({
        sub: body?.email ?? "e2e-user",
        exp: expiresAtEpoch,
        role,
        organization_id: organizationId,
        ...(role === "driver" ? { driver_id: seed.driver.id } : {}),
      });
      return ok(route, { access_token: accessToken, token_type: "Bearer", user: { role, organization_id: organizationId } });
    }

    if (path === "/auth/signup" && method === "POST") {
      const body = req.postDataJSON() as { email?: string; organization_name?: string };
      if ((body?.organization_name ?? "").toLowerCase().includes("duplicate")) {
        return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: { message: "Organization already exists" } }) });
      }
      const accessToken = buildToken({
        sub: body?.email ?? "owner.e2e@example.com",
        exp: Math.floor(Date.now() / 1000) + 60 * 60,
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
        updated_at: new Date().toISOString(),
      });
    }

    if (path === "/auth/me" && method === "GET") {
      return ok(route, { id: "staff-e2e-001", email: seed.owner.email, role: "owner", organization_id: seed.organizationId });
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

    if (path.includes("/loads/") && path.endsWith("/documents") && method === "GET") {
      return ok(route, state.documents.map((doc, index) => ({ id: `doc-${index + 1}`, file_name: `${doc}.pdf`, document_type: doc })));
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
            present_documents: state.documents,
          },
          amount_received: state.paidAmount,
          has_invoice: state.invoiceCount > 0,
          invoice_number: state.invoiceCount > 0 ? "INV-E2E-001" : null,
        });
      }
      return ok(route, [{ ...seed.load, status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready", driver_name: seed.driver.name }]);
    }

    if (path === "/documents/upload" && method === "POST") {
      state.documents.push("support");
      return created(route, { id: `doc-${Date.now()}` });
    }

    if (path === "/driver/documents/upload" && method === "POST") {
      state.documents.push("proof_of_delivery");
      return created(route, { id: `doc-driver-${Date.now()}` });
    }

    if (path.includes("/generate-invoice") && method === "POST") {
      if (state.invoiceCount === 0) {
        state.invoiceCount += 1;
      }
      return created(route, { id: "inv-e2e-001", invoice_number: "INV-E2E-001" });
    }

    if (path.includes("/submission-packets") && method === "POST") {
      state.packetCount += 1;
      return created(route, { id: `packet-${state.packetCount}`, packet_reference: "PKT-E2E-1", status: "created", documents: [], events: [] });
    }

    if (path.includes("/submission-packets") && method === "GET") {
      const packets = state.packetCount > 0 ? [{ id: "packet-1", packet_reference: "PKT-E2E-1", status: "created", destination_email: "ap@broker.test", documents: [{ id: "d1", document_type: "invoice" }], events: [{ id: "e1", event_type: "created", message: "Packet created" }] }] : [];
      return ok(route, packets);
    }

    if (path.includes("/submission-packets/") && path.endsWith("/download") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/zip", body: "PK\x03\x04" });
    }

    if (path.includes("/send-email") && method === "POST") {
      return ok(route, { status: "queued" });
    }

    if (path.includes("/loads/") && path.endsWith("/status") && method === "POST") {
      return ok(route, { new_status: "invoice_ready" });
    }

    if (path.includes("/driver/loads/") && path.endsWith("/check-in") && method === "POST") {
      return ok(route, { ...seed.load, status: "in_transit", driver_name: seed.driver.name });
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
      return created(route, { id: `pay-${Date.now()}`, amount_received: amount });
    }

    if (path.startsWith("/payments") && method === "GET") {
      return ok(route, []);
    }

    if (path.startsWith("/driver/loads") && method === "GET") {
      if (path === `/driver/loads/${seed.load.id}`) {
        return ok(route, { ...seed.load, driver_name: seed.driver.name, status: "delivered", packet_readiness: { present_documents: ["bill_of_lading"], missing_required_documents: { submission: ["proof_of_delivery"] } } });
      }
      return ok(route, [{ ...seed.load, status: "delivered", packet_readiness: { missing_required_documents: { submission: ["proof_of_delivery"] } } }]);
    }

    if (path.startsWith("/reports/money-dashboard") && method === "GET") {
      return ok(route, {
        summary: { total_receivables: 1000, total_outstanding: Math.max(0, 1000 - state.paidAmount), total_received: state.paidAmount, overdue_amount: 0, reserve_pending_amount: 0, disputed_count: 0, short_paid_count: 0 },
        aging_buckets: [],
        status_breakdown: [{ status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready", count: 1, amount: 1000 }],
        factoring_vs_direct: { factored: { count: 0, amount: 0 }, direct: { count: 1, amount: 1000 }, advance_total: 0, reserve_pending_total: 0, direct_unpaid_total: Math.max(0, 1000 - state.paidAmount) },
        needs_attention: { urgent_count: 0, overdue_followups_count: 0, top_items: [] },
        recent_cash_activity: [{ load_number: seed.load.load_number, amount_received: state.paidAmount, paid_date: new Date().toISOString(), payment_status: state.paidAmount >= 1000 ? "fully_paid" : "partial", factoring_used: false }],
      });
    }


    if (path === "/portal/me" && method === "GET") {
      const authHeader = req.headers().authorization ?? "";
      if (authHeader.includes("expired-portal-token")) {
        return error(route, 401, "This portal link is expired or invalid.", "portal_token_expired");
      }
      if (!authHeader.includes("valid-portal-token")) {
        return error(route, 401, "This portal link is expired or invalid.", "portal_token_invalid");
      }
      return ok(route, { scope: portalScope(), load: portalLoad() });
    }

    if (path === `/portal/loads/${seed.load.id}` && method === "GET") {
      const documents = state.portalDocuments.map((doc, index) => ({
        id: `portal-doc-${index + 1}`,
        document_type: doc,
        original_filename: `${doc}.pdf`,
        mime_type: "application/pdf",
        file_size_bytes: 2048,
        processing_status: "completed",
        received_at: "2026-05-09T00:00:00.000Z",
        download_allowed: true,
      }));
      return ok(route, {
        load: portalLoad(),
        documents,
        packets: [{ id: "portal-packet-1", packet_reference: "PKT-E2E-1", status: "created", sent_at: null, accepted_at: null, rejected_at: null, documents: [] }],
      });
    }

    if (path === `/portal/loads/${seed.load.id}/documents/upload` && method === "POST") {
      state.portalDocuments.unshift("accessorial_support");
      return created(route, {
        id: "portal-upload-1",
        document_type: "accessorial_support",
        original_filename: "sample-pod.png",
        mime_type: "image/png",
        file_size_bytes: 2048,
        processing_status: "completed",
        received_at: "2026-05-09T00:00:00.000Z",
        download_allowed: true,
      });
    }

    if (path.includes("/portal/loads/") && path.endsWith("/download") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/octet-stream", body: "portal-download" });
    }

    if (path.startsWith("/reports/operational-analytics") && method === "GET") {
      return ok(route, analyticsResponse());
    }

    if (path === "/operations/command-center" && method === "GET") {
      return ok(route, commandCenterResponse());
    }

    if (path === "/accounting/settings" && method === "GET") {
      return ok(route, {
        mapping: { accounting_category: "Freight Revenue", revenue_category: "Linehaul", factoring_category: "Factoring", settlement_category: "Settlements", payment_category: "Payments" },
        quickbooks: { provider: "quickbooks", enabled: false, default_export_format: "csv", sync_mode: "manual", last_export_note: null },
        quickbooks_capabilities: { provider: "quickbooks", sync_mode: "manual", supports_csv_exports: true, supports_direct_push: false, notes: "CSV exports only in E2E." },
      });
    }

    if (path.startsWith("/accounting/exports/") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "text/csv", body: "load_number,amount\nLD-E2E-001,1000\n" });
    }

    if (path.startsWith("/documents") && method === "GET") {
      return ok(route, state.documents.map((doc, index) => ({
        id: `doc-${index + 1}`,
        load_id: seed.load.id,
        load_number: seed.load.load_number,
        document_type: doc,
        original_filename: `${doc}.pdf`,
        file_name: `${doc}.pdf`,
        processing_status: "completed",
        received_at: "2026-05-09T00:00:00.000Z",
      })));
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
