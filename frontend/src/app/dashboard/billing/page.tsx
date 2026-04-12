"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type BillingMetrics = {
  active_subscriptions?: number;
  open_invoices?: number;
  past_due_invoices?: number;
  collected_this_month?: string | number | null;
  currency_code?: string | null;
};

type BillingSummaryResponse =
  | BillingMetrics
  | {
      data?: BillingMetrics;
      message?: string;
    };

type InvoiceListItem = {
  id: string;
  invoice_number: string;
  customer_account_id?: string | null;
  total_amount?: string | number | null;
  status: string;
  currency_code?: string | null;
};

type InvoiceListEnvelope = {
  items?: InvoiceListItem[];
  total?: number;
  page?: number;
  page_size?: number;
  pages?: number;
};

type InvoiceListResponse =
  | InvoiceListEnvelope
  | {
      data?: InvoiceListEnvelope;
      message?: string;
    };

function isWrappedResponse<T extends object>(
  value: unknown
): value is { data?: T; message?: string } {
  return typeof value === "object" && value !== null && ("data" in value || "message" in value);
}

function normalizeBillingMetrics(payload: BillingSummaryResponse | null): Required<BillingMetrics> {
  let root: BillingMetrics | null = null;

  if (isWrappedResponse<BillingMetrics>(payload)) {
    root = payload.data ?? null;
  } else if (payload && typeof payload === "object") {
    root = payload as BillingMetrics;
  }

  return {
    active_subscriptions: Number(root?.active_subscriptions ?? 0),
    open_invoices: Number(root?.open_invoices ?? 0),
    past_due_invoices: Number(root?.past_due_invoices ?? 0),
    collected_this_month: root?.collected_this_month ?? 0,
    currency_code: root?.currency_code?.trim() || "USD",
  };
}

function normalizeInvoiceList(payload: InvoiceListResponse | null): InvoiceListItem[] {
  let root: InvoiceListEnvelope | null = null;

  if (isWrappedResponse<InvoiceListEnvelope>(payload)) {
    root = payload.data ?? null;
  } else if (payload && typeof payload === "object") {
    root = payload as InvoiceListEnvelope;
  }

  return Array.isArray(root?.items) ? root.items : [];
}

function invoiceBadge(status: string) {
  switch (status) {
    case "paid":
      return "bg-emerald-100 text-emerald-800";
    case "open":
      return "bg-blue-100 text-blue-800";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    case "draft":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
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

export default function BillingPage() {
  const [metrics, setMetrics] = useState<Required<BillingMetrics>>({
    active_subscriptions: 0,
    open_invoices: 0,
    past_due_invoices: 0,
    collected_this_month: 0,
    currency_code: "USD",
  });
  const [recentInvoices, setRecentInvoices] = useState<InvoiceListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadBillingData(): Promise<void> {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage(null);

      const [summaryResponse, invoicesResponse] = await Promise.all([
        apiClient.get<BillingSummaryResponse>("/billing/dashboard", {
          token,
          organizationId,
        }),
        apiClient.get<InvoiceListResponse>("/billing-invoices?page=1&page_size=5", {
          token,
          organizationId,
        }),
      ]);

      setMetrics(normalizeBillingMetrics(summaryResponse));
      setRecentInvoices(normalizeInvoiceList(invoicesResponse));
    } catch (error) {
      setMetrics({
        active_subscriptions: 0,
        open_invoices: 0,
        past_due_invoices: 0,
        collected_this_month: 0,
        currency_code: "USD",
      });
      setRecentInvoices([]);
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : "An unexpected error occurred while loading billing data."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadBillingData();
  }, []);

  const billingSummary = useMemo(
    () => [
      { label: "Active Subscriptions", value: String(metrics.active_subscriptions) },
      { label: "Open Invoices", value: String(metrics.open_invoices) },
      { label: "Past Due", value: String(metrics.past_due_invoices) },
      {
        label: "Collected This Month",
        value: formatMoney(metrics.collected_this_month, metrics.currency_code),
      },
    ],
    [metrics]
  );

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review subscription performance, invoice status, payment activity, and account
              revenue signals.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => void loadBillingData()}
              disabled={isLoading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
            <Link
              href="/dashboard/billing/plans"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Plans
            </Link>
            <Link
              href="/dashboard/billing/invoices"
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Invoices
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-sm text-slate-600">Loading billing overview...</div>
          </div>
        ) : null}

        {!isLoading && errorMessage ? (
          <div className="mb-8 rounded-2xl border border-red-200 bg-red-50 p-6 shadow-soft">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-red-700">{errorMessage}</div>
              <button
                type="button"
                onClick={() => void loadBillingData()}
                className="inline-flex items-center rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-4">
          {billingSummary.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
            >
              <div className="text-sm text-slate-500">{item.label}</div>
              <div className="mt-2 text-3xl font-bold text-slate-950">{item.value}</div>
            </div>
          ))}
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.3fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-950">Recent Invoices</h2>
              <Link
                href="/dashboard/billing/invoices"
                className="text-sm font-semibold text-brand-700 hover:text-brand-800"
              >
                View all →
              </Link>
            </div>

            {recentInvoices.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                No recent invoices available.
              </div>
            ) : (
              <div className="space-y-3">
                {recentInvoices.map((invoice) => (
                  <Link
                    key={invoice.id}
                    href={`/dashboard/billing/invoices/${invoice.id}`}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                  >
                    <div>
                      <div className="text-sm font-semibold text-slate-900">
                        {invoice.invoice_number || "—"}
                      </div>
                      <div className="text-xs text-slate-500">
                        {invoice.customer_account_id || "—"}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-slate-900">
                        {formatMoney(invoice.total_amount, invoice.currency_code)}
                      </span>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${invoiceBadge(invoice.status)}`}
                      >
                        {(invoice.status || "unknown").replaceAll("_", " ")}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Billing Areas</h2>
              <div className="space-y-3">
                <Link
                  href="/dashboard/billing/plans"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Service Plans
                </Link>
                <Link
                  href="/dashboard/billing/subscriptions"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Subscriptions
                </Link>
                <Link
                  href="/dashboard/billing/invoices"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Invoices
                </Link>
                <Link
                  href="/dashboard/billing/payments"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Payments
                </Link>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Notes</h2>
              <p className="text-sm leading-6 text-slate-600">
                V1 billing is focused on subscription structure, invoice generation, payment
                tracking, and internal financial visibility. Advanced tax, discount, and refund
                workflows will follow later.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}