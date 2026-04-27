import { Page, Route } from "@playwright/test";
import { seed } from "../fixtures/test-data";

type MutableState = {
  invoiceCount: number;
  packetCount: number;
  documents: string[];
  paidAmount: number;
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

export async function mockApi(page: Page) {
  const state: MutableState = {
    invoiceCount: 0,
    packetCount: 0,
    documents: ["rate_confirmation", "bill_of_lading", "proof_of_delivery"],
    paidAmount: 0,
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
      return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { message: "Email sending is not enabled" } }) });
    }

    if (path.includes("/loads/") && path.endsWith("/status") && method === "POST") {
      return ok(route, { new_status: "invoice_ready" });
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

    if (path.startsWith("/billing/dashboard") && method === "GET") {
      return ok(route, { active_subscriptions: 0, open_invoices: 0, past_due_invoices: 0, collected_this_month: 0, currency_code: "USD" });
    }

    if (path.startsWith("/billing/invoices") && method === "GET") {
      return ok(route, { items: state.invoiceCount > 0 ? [{ id: "inv-e2e-001", invoice_number: "INV-E2E-001", status: "open", total_amount: 1000, currency_code: "USD", customer_account_id: seed.customer.id }] : [] });
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
