"use client";

import { useEffect, useMemo, useState } from "react";

type PaymentListItem = {
  id: string;
  customer_account_id?: string | null;
  invoice_id?: string | null;
  provider?: string | null;
  status: string;
  amount?: string | number | null;
  currency_code?: string | null;
  attempted_at?: string | null;
};

type PaymentListEnvelope = {
  items?: unknown;
  total?: unknown;
  page?: unknown;
  page_size?: unknown;
  pages?: unknown;
};

type PaymentListResponse =
  | PaymentListEnvelope
  | {
      data?: PaymentListEnvelope;
      message?: string;
    };

const DEFAULT_PAGE_SIZE = 25;

function getApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return value && value.length > 0 ? value.replace(/\/+$/, "") : "http://127.0.0.1:8000";
}

function readStoredValue(key: string): string {
  if (typeof window === "undefined") {
    return "";
  }

  return window.localStorage.getItem(key)?.trim() ?? "";
}

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

function normalizePaymentListItem(value: unknown): PaymentListItem | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = normalizeText(record.id);

  if (!id) {
    return null;
  }

  return {
    id,
    customer_account_id: normalizeText(record.customer_account_id),
    invoice_id: normalizeText(record.invoice_id),
    provider: normalizeText(record.provider),
    status: normalizeText(record.status) ?? "unknown",
    amount: normalizeNumberLike(record.amount),
    currency_code: normalizeText(record.currency_code) ?? "USD",
    attempted_at: normalizeText(record.attempted_at),
  };
}

function isPaymentListEnvelope(value: unknown): value is PaymentListEnvelope {
  return typeof value === "object" && value !== null && !Array.isArray(value) && !("message" in value);
}

function isWrappedPaymentListResponse(
  value: unknown
): value is { data?: PaymentListEnvelope; message?: string } {
  return typeof value === "object" && value !== null && !Array.isArray(value) && ("data" in value || "message" in value);
}

function normalizePaymentListResponse(payload: PaymentListResponse | null): {
  items: PaymentListItem[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
} {
  let root: PaymentListEnvelope | null = null;

  if (isWrappedPaymentListResponse(payload)) {
    root = payload.data ?? null;
  } else if (isPaymentListEnvelope(payload)) {
    root = payload;
  }

  if (!root) {
    return {
      items: [],
      total: 0,
      page: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      pages: 1,
    };
  }

  const rawItems = Array.isArray(root.items) ? root.items : [];
  const items = rawItems
    .map((item) => normalizePaymentListItem(item))
    .filter((item): item is PaymentListItem => item !== null);

  const totalFallback = items.length;
  const total = normalizePositiveInteger(root.total, totalFallback);
  const page = normalizePositiveInteger(root.page, 1);
  const pageSize = normalizePositiveInteger(root.page_size, DEFAULT_PAGE_SIZE);
  const computedPages = Math.max(1, Math.ceil(Math.max(total, items.length) / Math.max(1, pageSize)));
  const pages = normalizePositiveInteger(root.pages, computedPages);

  return {
    items,
    total: Math.max(total, items.length),
    page: Math.min(page, pages),
    pageSize,
    pages: Math.max(1, pages),
  };
}

function statusBadge(status: string) {
  switch (status.trim().toLowerCase()) {
    case "succeeded":
      return "bg-emerald-100 text-emerald-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    case "pending":
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

function formatDateTime(value: string | null | undefined): string {
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
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

export default function BillingPaymentsPage() {
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const [items, setItems] = useState<PaymentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);
  const [pages, setPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPayments(): Promise<void> {
      const token = readStoredValue("fbos_access_token");
      const tokenType = readStoredValue("fbos_token_type") || "Bearer";
      const organizationId = readStoredValue("fbos_organization_id");

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

        const url = new URL(`${apiBaseUrl}/api/v1/payments`);
        url.searchParams.set("page", String(safePage));
        url.searchParams.set("page_size", String(safePageSize));

        const response = await fetch(url.toString(), {
          method: "GET",
          headers: {
            Accept: "application/json",
            Authorization: `${tokenType} ${token}`,
            "X-Organization-Id": organizationId,
          },
          cache: "no-store",
          signal: controller.signal,
        });

        let payload: PaymentListResponse | null = null;
        try {
          payload = (await response.json()) as PaymentListResponse;
        } catch {
          payload = null;
        }

        if (!response.ok) {
          const message =
            payload &&
            typeof payload === "object" &&
            "message" in payload &&
            typeof payload.message === "string" &&
            payload.message.trim()
              ? payload.message.trim()
              : "Unable to load payments.";
          throw new Error(message);
        }

        const normalized = normalizePaymentListResponse(payload);

        if (controller.signal.aborted) {
          return;
        }

        setItems(normalized.items);
        setTotal(normalized.total);
        setPages(normalized.pages);

        if (normalized.page !== safePage) {
          setPage(normalized.page);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setItems([]);
        setTotal(0);
        setPages(1);
        setErrorMessage(
          error instanceof Error && error.message
            ? error.message
            : "An unexpected error occurred while loading payments."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadPayments();

    return () => {
      controller.abort();
    };
  }, [apiBaseUrl, page, pageSize, reloadKey]);

  const canGoPrevious = page > 1;
  const canGoNext = page < pages;

  function handleRetry(): void {
    setReloadKey((current) => current + 1);
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Payments</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Payments</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review payment attempts, success and failure states, invoice linkage, and collected
              amounts.
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
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              Record Payment
            </button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          {isLoading ? (
            <div className="px-6 py-12 text-sm text-slate-600">Loading payments...</div>
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
              No payments found for this organization.
            </div>
          ) : null}

          {!isLoading && !errorMessage && items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-slate-600">
                      <th className="px-5 py-4 font-semibold">Payment</th>
                      <th className="px-5 py-4 font-semibold">Customer</th>
                      <th className="px-5 py-4 font-semibold">Invoice</th>
                      <th className="px-5 py-4 font-semibold">Provider</th>
                      <th className="px-5 py-4 font-semibold">Status</th>
                      <th className="px-5 py-4 font-semibold">Amount</th>
                      <th className="px-5 py-4 font-semibold">Attempted At</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {items.map((payment) => (
                      <tr key={payment.id} className="hover:bg-slate-50">
                        <td className="px-5 py-4">
                          <div className="font-semibold text-slate-900">{payment.id}</div>
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {payment.customer_account_id || "—"}
                        </td>
                        <td className="px-5 py-4 text-slate-700">{payment.invoice_id || "—"}</td>
                        <td className="px-5 py-4 text-slate-700">{payment.provider || "—"}</td>
                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                              payment.status
                            )}`}
                          >
                            {payment.status || "unknown"}
                          </span>
                        </td>
                        <td className="px-5 py-4 font-medium text-slate-900">
                          {formatMoney(payment.amount, payment.currency_code)}
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {formatDateTime(payment.attempted_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-slate-600">
                  Showing page {page} of {pages} · {total} total payment{total === 1 ? "" : "s"}
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