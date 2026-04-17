"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type TokenClaims = {
  role?: string;
  driver_id?: string;
};

type BillingInvoice = {
  id: string;
  invoice_number?: string | null;
  status?: string | null;
  total_amount?: string | number | null;
  amount_due?: string | number | null;
  currency_code?: string | null;
  due_at?: string | null;
};

type Payment = {
  id: string;
  status?: string | null;
  amount?: string | number | null;
  currency_code?: string | null;
  attempted_at?: string | null;
};

type Subscription = {
  id: string;
  status?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function normalizeList(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  const root = asRecord(payload);
  if (!root) {
    return [];
  }

  if (Array.isArray(root.data)) {
    return root.data;
  }

  if (Array.isArray(root.items)) {
    return root.items;
  }

  return [];
}

function parseClaims(token: string | null): TokenClaims {
  if (!token) return {};

  const parts = token.split(".");
  if (parts.length < 2) return {};

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded = window.atob(padded);
    const record = asRecord(JSON.parse(decoded));

    if (!record) return {};

    return {
      role: typeof record.role === "string" ? record.role : undefined,
      driver_id: typeof record.driver_id === "string" ? record.driver_id : undefined,
    };
  } catch {
    return {};
  }
}

function formatMoney(value: string | number | null | undefined, currencyCode?: string | null): string {
  const numeric = Number(value ?? 0);

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  const normalizedCurrency = currencyCode?.trim() || "USD";

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: normalizedCurrency,
    }).format(numeric);
  } catch {
    return `${normalizedCurrency} ${numeric.toFixed(2)}`;
  }
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("en-US");
}

function normalizeInvoice(item: unknown): BillingInvoice | null {
  const row = asRecord(item);
  if (!row || typeof row.id !== "string") return null;

  return {
    id: row.id,
    invoice_number: typeof row.invoice_number === "string" ? row.invoice_number : null,
    status: typeof row.status === "string" ? row.status : null,
    total_amount: (row.total_amount as string | number | null | undefined) ?? null,
    amount_due: (row.amount_due as string | number | null | undefined) ?? null,
    currency_code: typeof row.currency_code === "string" ? row.currency_code : "USD",
    due_at: typeof row.due_at === "string" ? row.due_at : null,
  };
}

function normalizePayment(item: unknown): Payment | null {
  const row = asRecord(item);
  if (!row || typeof row.id !== "string") return null;

  return {
    id: row.id,
    status: typeof row.status === "string" ? row.status : null,
    amount: (row.amount as string | number | null | undefined) ?? null,
    currency_code: typeof row.currency_code === "string" ? row.currency_code : "USD",
    attempted_at: typeof row.attempted_at === "string" ? row.attempted_at : null,
  };
}

function normalizeSubscription(item: unknown): Subscription | null {
  const row = asRecord(item);
  if (!row || typeof row.id !== "string") return null;

  return {
    id: row.id,
    status: typeof row.status === "string" ? row.status : null,
  };
}

export default function DriverBillingPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<BillingInvoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);

  const token = getAccessToken();
  const organizationId = getOrganizationId();
  const claims = useMemo(() => parseClaims(token), [token]);

  useEffect(() => {
    if (!token || !organizationId || !claims.driver_id) {
      setIsLoading(false);
      setErrorMessage("Missing driver billing context. Please sign in again.");
      return;
    }

    let mounted = true;

    async function loadData() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const [invoicePayload, paymentPayload, subscriptionPayload] = await Promise.all([
          apiClient.get(`/billing-invoices?driver_id=${claims.driver_id}&page=1&page_size=5`, {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }),
          apiClient.get(`/payments?driver_id=${claims.driver_id}&page=1&page_size=5`, {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }),
          apiClient.get("/subscriptions?page=1&page_size=5", {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }),
        ]);

        if (!mounted) return;

        setInvoices(normalizeList(invoicePayload).map(normalizeInvoice).filter((item): item is BillingInvoice => item !== null));
        setPayments(normalizeList(paymentPayload).map(normalizePayment).filter((item): item is Payment => item !== null));
        setSubscriptions(normalizeList(subscriptionPayload).map(normalizeSubscription).filter((item): item is Subscription => item !== null));
      } catch (error) {
        if (!mounted) return;
        setErrorMessage(error instanceof Error ? error.message : "Unable to load billing overview.");
        setInvoices([]);
        setPayments([]);
        setSubscriptions([]);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void loadData();

    return () => {
      mounted = false;
    };
  }, [claims.driver_id, organizationId, token]);

  const openInvoices = invoices.filter((item) => (item.status ?? "").toLowerCase() !== "paid");
  const totalDue = openInvoices.reduce((sum, invoice) => sum + Number(invoice.amount_due ?? 0), 0);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing Overview</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Review your driver-scoped invoice and payment activity with live organization billing records.
          </p>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Invoices</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{isLoading ? "..." : invoices.length}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Open / Past Due</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">{isLoading ? "..." : openInvoices.length}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Amount Due</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{isLoading ? "..." : formatMoney(totalDue, invoices[0]?.currency_code)}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Payments</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">{isLoading ? "..." : payments.length}</div>
          </div>
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-950">Recent Invoices</h2>
              <Link href="/driver-portal/billing/invoices" className="text-sm font-semibold text-brand-700">View all →</Link>
            </div>
            {invoices.length === 0 ? (
              <p className="text-sm text-slate-500">No driver-linked invoices found.</p>
            ) : (
              <div className="space-y-3">
                {invoices.slice(0, 3).map((invoice) => (
                  <div key={invoice.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
                    <div className="font-semibold text-slate-900">{invoice.invoice_number || invoice.id}</div>
                    <div className="mt-1 text-slate-600">
                      Due {formatDate(invoice.due_at)} · {formatMoney(invoice.amount_due, invoice.currency_code)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-950">Recent Payments</h2>
              <Link href="/driver-portal/billing/payments" className="text-sm font-semibold text-brand-700">View all →</Link>
            </div>
            {payments.length === 0 ? (
              <p className="text-sm text-slate-500">No driver-linked payments found.</p>
            ) : (
              <div className="space-y-3">
                {payments.slice(0, 3).map((payment) => (
                  <div key={payment.id} className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
                    <div className="font-semibold text-slate-900">{formatMoney(payment.amount, payment.currency_code)}</div>
                    <div className="mt-1 text-slate-600">
                      {(payment.status || "unknown").replaceAll("_", " ")} · {formatDate(payment.attempted_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <p className="mt-4 text-xs text-slate-500">
              Subscription records are organization-level in V1 ({subscriptions.length} currently visible), so this overview keeps that section informational.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
