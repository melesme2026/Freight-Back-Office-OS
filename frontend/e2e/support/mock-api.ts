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
      const body = req.postDataJSON() as { email?: string; password?: string };
      if (body?.password !== seed.owner.password) {
        return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { message: "Invalid credentials" } }) });
      }
      const role = body.email === seed.driver.email ? "driver" : "owner";
      return ok(route, { access_token: "header.payload.signature", token_type: "Bearer", user: { role, organization_id: seed.organizationId } });
    }

    if (path === "/auth/signup" && method === "POST") {
      const body = req.postDataJSON() as { email?: string; organization_name?: string };
      if ((body?.organization_name ?? "").toLowerCase().includes("duplicate")) {
        return route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: { message: "Organization already exists" } }) });
      }
      return created(route, { access_token: "header.payload.signature", token_type: "Bearer", user: { role: "owner", organization_id: seed.organizationId, email: body.email } });
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

    if (path.includes("/send-email") && method === "POST") {
      return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { message: "Email sending is not enabled" } }) });
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

    if (path.startsWith("/money/dashboard") && method === "GET") {
      return ok(route, {
        summary: { total_receivables: 1000, total_outstanding: Math.max(0, 1000 - state.paidAmount), total_received: state.paidAmount, overdue_amount: 0, reserve_pending_amount: 0, disputed_count: 0, short_paid_count: 0 },
        status_breakdown: [{ status: state.paidAmount >= 1000 ? "fully_paid" : "invoice_ready", count: 1, amount: 1000 }],
        factoring_vs_direct: { factored: { count: 0, amount: 0 }, direct: { count: 1, amount: 1000 }, advance_total: 0, reserve_pending_total: 0, direct_unpaid_total: Math.max(0, 1000 - state.paidAmount) },
        recent_cash_activity: [{ load_number: seed.load.load_number, amount_received: state.paidAmount, paid_date: new Date().toISOString(), payment_status: state.paidAmount >= 1000 ? "fully_paid" : "partial", factoring_used: false }],
      });
    }

    if (path.startsWith("/billing/summary") && method === "GET") {
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

    return ok(route, []);
  });
}
