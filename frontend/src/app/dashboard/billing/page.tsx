"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type BillingMetrics = {
  active_subscriptions?: number;
  active_subscriptions_count?: number;
  open_invoices?: number;
  open_invoices_count?: number;
  past_due_invoices?: number;
  past_due_invoices_count?: number;
  collected_this_month?: string | number | null;
  payments_collected_this_month?: string | number | null;
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
  invoice_number?: string | null;
  customer_account_id?: string | null;
  total_amount?: string | number | null;
  status?: string | null;
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
      data?: InvoiceListEnvelope | InvoiceListItem[];
      meta?: { total?: number; page?: number; page_size?: number; pages?: number };
      message?: string;
    };

type NormalizedInvoiceListItem = {
  id: string;
  invoiceNumber: string;
  customerAccountId: string;
  totalAmount: string | number | null;
  status: string;
  currencyCode: string;
};

function isWrappedResponse<T extends object>(
  value: unknown
): value is { data?: T; message?: string } {
  return typeof value === "object" && value !== null && ("data" in value || "message" in value);
}

type NormalizedBillingMetrics = {
  active_subscriptions: number;
  open_invoices: number;
  past_due_invoices: number;
  collected_this_month: string | number | null;
  currency_code: string;
};

function normalizeBillingMetrics(payload: BillingSummaryResponse | null): NormalizedBillingMetrics {
  let root: BillingMetrics | null = null;

  if (isWrappedResponse<BillingMetrics>(payload)) {
    root = payload.data ?? null;
  } else if (payload && typeof payload === "object") {
    root = payload as BillingMetrics;
  }

  return {
    active_subscriptions: Number(root?.active_subscriptions ?? root?.active_subscriptions_count ?? 0),
    open_invoices: Number(root?.open_invoices ?? root?.open_invoices_count ?? 0),
    past_due_invoices: Number(root?.past_due_invoices ?? root?.past_due_invoices_count ?? 0),
    collected_this_month: root?.collected_this_month ?? root?.payments_collected_this_month ?? 0,
    currency_code: root?.currency_code?.trim() || "USD",
  };
}

function normalizeInvoiceStatus(status: string | null | undefined): string {
  return (status ?? "unknown").trim().toLowerCase().replaceAll(" ", "_");
}

function normalizeInvoiceList(payload: InvoiceListResponse | null): NormalizedInvoiceListItem[] {
  let rawItems: InvoiceListItem[] = [];

  if (isWrappedResponse<InvoiceListEnvelope | InvoiceListItem[]>(payload)) {
    if (Array.isArray(payload.data)) {
      rawItems = payload.data;
    } else if (payload.data && typeof payload.data === "object" && Array.isArray(payload.data.items)) {
      rawItems = payload.data.items;
    }
  } else if (payload && typeof payload === "object" && Array.isArray((payload as InvoiceListEnvelope).items)) {
    rawItems = (payload as InvoiceListEnvelope).items ?? [];
  }

  return rawItems
    .filter((item): item is InvoiceListItem & { id: string } => typeof item?.id === "string" && item.id.length > 0)
    .map((item) => ({
      id: item.id,
      invoiceNumber: item.invoice_number?.trim() || "—",
      customerAccountId: item.customer_account_id?.trim() || "—",
      totalAmount: item.total_amount ?? 0,
      status: normalizeInvoiceStatus(item.status),
      currencyCode: item.currency_code?.trim() || "USD",
    }));
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

function formatStatusLabel(status: string): string {
  if (!status) {
    return "Unknown";
  }

  return status
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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
  const [metrics, setMetrics] = useState<NormalizedBillingMetrics>({
    active_subscriptions: 0,
    open_invoices: 0,
    past_due_invoices: 0,
    collected_this_month: 0,
    currency_code: "USD",
  });
  const [recentInvoices, setRecentInvoices] = useState<NormalizedInvoiceListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isMountedRef = useRef(true);

  const loadBillingData = useCallback(async (mode: "initial" | "refresh" = "initial"): Promise<void> => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      if (!isMountedRef.current) {
        return;
      }

      setErrorMessage("Missing session context. Please sign in again.");
      setIsLoading(false);
      setIsRefreshing(false);
      return;
    }

    try {
      if (mode === "initial") {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }

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

      if (!isMountedRef.current) {
        return;
      }

      setMetrics(normalizeBillingMetrics(summaryResponse));
      setRecentInvoices(normalizeInvoiceList(invoicesResponse));
    } catch (error) {
      if (!isMountedRef.current) {
        return;
      }

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
      if (!isMountedRef.current) {
        return;
      }

      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    void loadBillingData("initial");

    return () => {
      isMountedRef.current = false;
    };
  }, [loadBillingData]);

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
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Review subscription performance, invoice status, payment activity, and account revenue signals.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void loadBillingData("refresh")}
              disabled={isLoading || isRefreshing}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button>
            <Link
              href="/dashboard/billing/plans"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Plans
            </Link>
            <Link
              href="/dashboard/billing/invoices"
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
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
                onClick={() => void loadBillingData("refresh")}
                disabled={isRefreshing}
                className="inline-flex items-center rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRefreshing ? "Retrying..." : "Retry"}
              </button>
            </div>
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {billingSummary.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
            >
              <div className="text-sm text-slate-500">{item.label}</div>
              <div className="mt-2 break-words text-3xl font-bold text-slate-950">{item.value}</div>
            </div>
          ))}
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.3fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-950">Recent Invoices</h2>
              <Link
                href="/dashboard/billing/invoices"
                className="text-sm font-semibold text-brand-700 transition hover:text-brand-800"
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
                    className="flex flex-col gap-3 rounded-xl border border-slate-200 px-4 py-3 transition hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-900">
                        {invoice.invoiceNumber}
                      </div>
                      <div className="truncate text-xs text-slate-500">
                        {invoice.customerAccountId}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 sm:justify-end">
                      <span className="text-sm font-medium text-slate-900">
                        {formatMoney(invoice.totalAmount, invoice.currencyCode)}
                      </span>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${invoiceBadge(invoice.status)}`}
                      >
                        {formatStatusLabel(invoice.status)}
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
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Service Plans
                </Link>
                <Link
                  href="/dashboard/billing/subscriptions"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Subscriptions
                </Link>
                <Link
                  href="/dashboard/billing/invoices"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Invoices
                </Link>
                <Link
                  href="/dashboard/billing/payments"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Payments
                </Link>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Release Notes</h2>
              <p className="text-sm leading-6 text-slate-600">
                Billing V1 is focused on subscription structure, invoice generation, payment tracking,
                and internal financial visibility. Advanced tax, discount, refund, and reconciliation
                workflows should only be exposed once backend support is fully implemented.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}