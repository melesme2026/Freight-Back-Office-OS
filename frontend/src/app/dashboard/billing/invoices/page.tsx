"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type InvoiceListItem = {
  id: string;
  invoice_number: string;
  customer_account_id: string | null;
  status: string;
  total_amount: string | number | null;
  amount_due: string | number | null;
  issued_at: string | null;
  due_at: string | null;
  currency_code: string | null;
};

type InvoiceListEnvelope = {
  items?: unknown;
  total?: unknown;
  page?: unknown;
  page_size?: unknown;
  pages?: unknown;
};

type ResponseMeta = {
  total?: unknown;
  page?: unknown;
  page_size?: unknown;
  pages?: unknown;
};

type WrappedInvoiceListResponse = {
  data?: unknown;
  meta?: ResponseMeta;
  message?: unknown;
};

const DEFAULT_PAGE_SIZE = 25;

function normalizeText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeNumberLike(value: unknown): string | number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  return null;
}

function normalizePositiveInteger(value: unknown, fallback: number): number {
  const numeric =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number.parseInt(value, 10)
        : Number.NaN;

  if (!Number.isFinite(numeric) || numeric <= 0) {
    return fallback;
  }

  return Math.floor(numeric);
}

function normalizeInvoiceListItem(value: unknown): InvoiceListItem | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = normalizeText(record.id);
  const invoiceNumber = normalizeText(record.invoice_number);

  if (!id || !invoiceNumber) {
    return null;
  }

  return {
    id,
    invoice_number: invoiceNumber,
    customer_account_id: normalizeText(record.customer_account_id),
    status: normalizeText(record.status) ?? "unknown",
    total_amount: normalizeNumberLike(record.total_amount),
    amount_due: normalizeNumberLike(record.amount_due),
    issued_at: normalizeText(record.issued_at),
    due_at: normalizeText(record.due_at),
    currency_code: normalizeText(record.currency_code) ?? "USD",
  };
}

function isEnvelope(value: unknown): value is InvoiceListEnvelope {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function isWrappedResponse(value: unknown): value is WrappedInvoiceListResponse {
  return !!value && typeof value === "object" && !Array.isArray(value) && "data" in value;
}

function normalizeInvoiceListResponse(payload: unknown): {
  items: InvoiceListItem[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
} {
  let rawItems: unknown[] = [];
  let meta: ResponseMeta | null = null;

  if (isWrappedResponse(payload)) {
    if (Array.isArray(payload.data)) {
      rawItems = payload.data;
      meta = isEnvelope(payload.meta) ? payload.meta : null;
    } else if (isEnvelope(payload.data)) {
      const nestedRoot = payload.data;
      rawItems = Array.isArray(nestedRoot.items) ? nestedRoot.items : [];
      meta = nestedRoot;
    }
  } else if (Array.isArray(payload)) {
    rawItems = payload;
  } else if (isEnvelope(payload)) {
    rawItems = Array.isArray(payload.items) ? payload.items : [];
    meta = payload;
  }

  const items = rawItems
    .map((item) => normalizeInvoiceListItem(item))
    .filter((item): item is InvoiceListItem => item !== null);

  const totalFallback = items.length;
  const total = normalizePositiveInteger(meta?.total, totalFallback);
  const page = normalizePositiveInteger(meta?.page, 1);
  const pageSize = normalizePositiveInteger(meta?.page_size, DEFAULT_PAGE_SIZE);
  const computedPages = Math.max(1, Math.ceil(Math.max(total, items.length) / Math.max(1, pageSize)));
  const pages = normalizePositiveInteger(meta?.pages, computedPages);

  return {
    items,
    total: Math.max(total, items.length),
    page: Math.min(page, Math.max(1, pages)),
    pageSize,
    pages: Math.max(1, pages),
  };
}

function statusBadge(status?: string) {
  switch ((status ?? "").trim().toLowerCase()) {
    case "paid":
      return "bg-emerald-100 text-emerald-800";
    case "open":
      return "bg-blue-100 text-blue-800";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    case "draft":
      return "bg-amber-100 text-amber-800";
    case "cancelled":
      return "bg-slate-200 text-slate-700";
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

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(parsed);
}

export default function BillingInvoicesPage() {
  const router = useRouter();
  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [pages, setPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadInvoices(): Promise<void> {
      const token = getAccessToken();
      const organizationId = getOrganizationId();

      if (!token || !organizationId) {
        setItems([]);
        setTotal(0);
        setPages(1);
        setErrorMessage("Missing session context. Please sign in again.");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setErrorMessage(null);

        const safePage = Math.max(1, page);
        const safePageSize = Math.max(1, pageSize);

        const payload = await apiClient.get<unknown>(`/billing-invoices?page=${safePage}&page_size=${safePageSize}`, {
          token,
          organizationId,
          signal: controller.signal,
        });

        const normalized = normalizeInvoiceListResponse(payload);

        if (controller.signal.aborted) {
          return;
        }

        setItems(normalized.items);
        setTotal(normalized.total);
        setPages(normalized.pages);

        if (normalized.page !== safePage) {
          setPage(normalized.page);
        }
      } catch (error: unknown) {
        if (controller.signal.aborted) {
          return;
        }

        setItems([]);
        setTotal(0);
        setPages(1);
        setErrorMessage(
          error instanceof Error && error.message
            ? error.message
            : "An unexpected error occurred while loading invoices."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadInvoices();

    return () => {
      controller.abort();
    };
  }, [page, pageSize, reloadKey]);

  const canGoPrevious = page > 1;
  const canGoNext = page < pages;

  function handleRetry(): void {
    setReloadKey((current) => current + 1);
  }

  function openInvoiceDetail(invoiceId: string): void {
    router.push(`/dashboard/billing/invoices/${invoiceId}`);
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Invoices</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Invoices</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review issued invoices, open balances, due dates, and customer billing status.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleRetry}
              disabled={isLoading}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-soft transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>

            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Invoice creation is not yet available in V1."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              New Invoice
            </button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          {isLoading ? (
            <div className="px-6 py-12 text-sm text-slate-600">Loading invoices...</div>
          ) : null}

          {!isLoading && errorMessage ? (
            <div className="px-6 py-12">
              <div className="flex flex-col gap-4 rounded-xl border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between">
                <div>{errorMessage}</div>
                <button
                  type="button"
                  onClick={handleRetry}
                  className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : null}

          {!isLoading && !errorMessage && items.length === 0 ? (
            <div className="px-6 py-12 text-sm text-slate-600">
              No invoices found for this organization.
            </div>
          ) : null}

          {!isLoading && !errorMessage && items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-slate-600">
                      <th className="px-5 py-4 font-semibold">Invoice</th>
                      <th className="px-5 py-4 font-semibold">Customer</th>
                      <th className="px-5 py-4 font-semibold">Status</th>
                      <th className="px-5 py-4 font-semibold">Total</th>
                      <th className="px-5 py-4 font-semibold">Amount Due</th>
                      <th className="px-5 py-4 font-semibold">Issued</th>
                      <th className="px-5 py-4 font-semibold">Due</th>
                      <th className="px-5 py-4 font-semibold">Action</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {items.map((invoice) => (
                      <tr key={invoice.id} className="hover:bg-slate-50">
                        <td className="px-5 py-4">
                          <div className="font-semibold text-slate-900">
                            {invoice.invoice_number}
                          </div>
                          <div className="text-xs text-slate-500">{invoice.id}</div>
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {invoice.customer_account_id ?? "—"}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                              invoice.status
                            )}`}
                          >
                            {invoice.status.replaceAll("_", " ")}
                          </span>
                        </td>

                        <td className="px-5 py-4 font-medium text-slate-900">
                          {formatMoney(invoice.total_amount, invoice.currency_code)}
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatMoney(invoice.amount_due, invoice.currency_code)}
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatDate(invoice.issued_at)}
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatDate(invoice.due_at)}
                        </td>

                        <td className="px-5 py-4">
                          <button
                            type="button"
                            onClick={() => openInvoiceDetail(invoice.id)}
                            className="text-sm font-semibold text-brand-700 transition hover:text-brand-800"
                          >
                            View →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-slate-600">
                  Showing page {page} of {pages} · {total} total invoice{total === 1 ? "" : "s"}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    disabled={!canGoPrevious}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((current) => Math.min(pages, current + 1))}
                    disabled={!canGoNext}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </section>
      </div>
    </main>
  );
}