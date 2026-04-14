"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { buildApiUrl } from "@/lib/config";

type InvoiceLine = {
  id: string;
  line_type: string;
  description: string;
  quantity: string | number;
  unit_price: string | number | null;
  line_total: string | number | null;
};

type InvoiceRecord = {
  id: string;
  invoice_number: string;
  customer_account_id?: string | null;
  status: string;
  currency_code: string;
  subtotal_amount?: string | number | null;
  tax_amount?: string | number | null;
  total_amount?: string | number | null;
  amount_paid?: string | number | null;
  amount_due?: string | number | null;
  issued_at?: string | null;
  due_at?: string | null;
  billing_period_start?: string | null;
  billing_period_end?: string | null;
  notes?: string | null;
  lines?: InvoiceLine[];
};

type InvoiceResponse =
  | InvoiceRecord
  | {
      data?: InvoiceRecord | null;
      message?: string;
    };

function readStoredValue(key: string): string {
  if (typeof window === "undefined") {
    return "";
  }

  const value = window.localStorage.getItem(key);
  return typeof value === "string" ? value.trim() : "";
}

function normalizeRouteParam(value: string | string[] | undefined): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (Array.isArray(value) && value.length > 0) {
    const first = value[0];
    if (typeof first === "string") {
      const trimmed = first.trim();
      return trimmed.length > 0 ? trimmed : null;
    }
  }

  return null;
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

function normalizeInvoiceLine(value: unknown): InvoiceLine | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;

  const fallbackIdParts = [
    normalizeText(record.line_type) ?? "line",
    normalizeText(record.description) ?? "item",
    String(normalizeNumberLike(record.quantity) ?? "0"),
  ];

  return {
    id: normalizeText(record.id) ?? fallbackIdParts.join("-"),
    line_type: normalizeText(record.line_type) ?? "unknown",
    description: normalizeText(record.description) ?? "Line item",
    quantity: normalizeNumberLike(record.quantity) ?? "0",
    unit_price: normalizeNumberLike(record.unit_price),
    line_total: normalizeNumberLike(record.line_total),
  };
}

function normalizeInvoiceRecord(value: unknown): InvoiceRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = normalizeText(record.id);
  const invoiceNumber = normalizeText(record.invoice_number);

  if (!id || !invoiceNumber) {
    return null;
  }

  const rawLines = Array.isArray(record.lines) ? record.lines : [];

  return {
    id,
    invoice_number: invoiceNumber,
    customer_account_id: normalizeText(record.customer_account_id),
    status: normalizeText(record.status) ?? "unknown",
    currency_code: normalizeText(record.currency_code) ?? "USD",
    subtotal_amount: normalizeNumberLike(record.subtotal_amount),
    tax_amount: normalizeNumberLike(record.tax_amount),
    total_amount: normalizeNumberLike(record.total_amount),
    amount_paid: normalizeNumberLike(record.amount_paid),
    amount_due: normalizeNumberLike(record.amount_due),
    issued_at: normalizeText(record.issued_at),
    due_at: normalizeText(record.due_at),
    billing_period_start: normalizeText(record.billing_period_start),
    billing_period_end: normalizeText(record.billing_period_end),
    notes: normalizeText(record.notes),
    lines: rawLines
      .map((line) => normalizeInvoiceLine(line))
      .filter((line): line is InvoiceLine => line !== null),
  };
}

function normalizeInvoiceResponse(payload: unknown): InvoiceRecord | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;

  if ("data" in record) {
    return normalizeInvoiceRecord(record.data);
  }

  return normalizeInvoiceRecord(record);
}

function extractErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const record = payload as Record<string, unknown>;
  return normalizeText(record.message);
}

function formatMoney(value: string | number | null | undefined, currencyCode: string): string {
  const numeric = Number(value ?? 0);

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode || "USD",
    }).format(numeric);
  } catch {
    return `${currencyCode || "USD"} ${numeric.toFixed(2)}`;
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

function getStatusBadgeClass(status: string): string {
  switch (status.trim().toLowerCase()) {
    case "paid":
      return "bg-emerald-100 text-emerald-800";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    case "cancelled":
      return "bg-slate-200 text-slate-700";
    case "draft":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-blue-100 text-blue-800";
  }
}

export default function InvoiceDetailPage() {
  const router = useRouter();
  const params = useParams<{ invoiceId: string | string[] }>();
  const invoiceId = normalizeRouteParam(params?.invoiceId);

  const [invoice, setInvoice] = useState<InvoiceRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadInvoice(): Promise<void> {
      if (!invoiceId) {
        setInvoice(null);
        setErrorMessage("Invoice ID is missing.");
        setIsLoading(false);
        return;
      }

      const token = readStoredValue("fbos_access_token");
      const tokenType = readStoredValue("fbos_token_type") || "Bearer";
      const organizationId = readStoredValue("fbos_organization_id");

      if (!token || !organizationId) {
        setInvoice(null);
        setErrorMessage("Missing session context. Please sign in again.");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setErrorMessage(null);

        const response = await fetch(
          buildApiUrl(`/billing-invoices/${encodeURIComponent(invoiceId)}`),
          {
            method: "GET",
            headers: {
              Accept: "application/json",
              Authorization: `${tokenType} ${token}`,
              "X-Organization-Id": organizationId,
            },
            cache: "no-store",
            signal: controller.signal,
          }
        );

        let payload: unknown = null;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }

        if (!response.ok) {
          throw new Error(extractErrorMessage(payload) ?? "Unable to load invoice details.");
        }

        const normalized = normalizeInvoiceResponse(payload);
        if (!normalized) {
          throw new Error("Invoice response was not in the expected format.");
        }

        setInvoice(normalized);
      } catch (error: unknown) {
        if (controller.signal.aborted) {
          return;
        }

        setInvoice(null);
        setErrorMessage(
          error instanceof Error && error.message
            ? error.message
            : "An unexpected error occurred while loading the invoice."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadInvoice();

    return () => {
      controller.abort();
    };
  }, [invoiceId, reloadKey]);

  const currencyCode = invoice?.currency_code ?? "USD";
  const lines = Array.isArray(invoice?.lines) ? invoice.lines : [];
  const status = invoice?.status ?? "unknown";
  const statusBadge = getStatusBadgeClass(status);

  function handleRetry(): void {
    setReloadKey((current) => current + 1);
  }

  function handleBackToInvoices(): void {
    router.push("/dashboard/billing/invoices");
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Billing / Invoices / Detail
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {isLoading ? "Loading invoice..." : invoice?.invoice_number ?? "Invoice Detail"}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Invoice detail including totals, billing period, line items, and payment readiness.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleBackToInvoices}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Back to Invoices
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-400"
            >
              Mark Paid
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="rounded-xl bg-brand-300 px-4 py-2 text-sm font-semibold text-white"
            >
              Collect Payment
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-sm text-slate-600">Loading invoice detail...</div>
          </div>
        ) : null}

        {!isLoading && errorMessage ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-soft">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-red-800">Unable to load invoice</h2>
                <p className="mt-2 text-sm leading-6 text-red-700">{errorMessage}</p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleRetry}
                  className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
                >
                  Retry
                </button>
                <button
                  type="button"
                  onClick={handleBackToInvoices}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Back to Invoices
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {!isLoading && !errorMessage && invoice ? (
          <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
            <section className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <div className="mb-5 flex items-center justify-between gap-4">
                  <h2 className="text-lg font-semibold text-slate-950">Invoice Summary</h2>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge}`}>
                    {status.replaceAll("_", " ")}
                  </span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">
                      {invoice.customer_account_id ?? "—"}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Currency</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">{currencyCode}</div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Issued At</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">
                      {formatDate(invoice.issued_at)}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Due At</div>
                    <div className="mt-1 text-sm font-medium text-slate-900">
                      {formatDate(invoice.due_at)}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Billing Period
                    </div>
                    <div className="mt-1 text-sm font-medium text-slate-900">
                      {formatDate(invoice.billing_period_start)} →{" "}
                      {formatDate(invoice.billing_period_end)}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Invoice ID</div>
                    <div className="mt-1 break-all text-sm font-medium text-slate-900">
                      {invoice.id}
                    </div>
                  </div>
                </div>

                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Notes</div>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {invoice.notes ?? "No notes available."}
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <h2 className="mb-4 text-lg font-semibold text-slate-950">Invoice Lines</h2>

                {lines.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
                    No invoice lines were returned.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {lines.map((line, index) => (
                      <div
                        key={line.id || `${line.description}-${index}`}
                        className="rounded-xl border border-slate-200 px-4 py-4"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="text-sm font-semibold text-slate-900">
                              {line.description || "Line item"}
                            </div>
                            <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                              {line.line_type || "unknown"}
                            </div>
                          </div>

                          <div className="text-right">
                            <div className="text-sm font-semibold text-slate-900">
                              {formatMoney(line.line_total, currencyCode)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                              {String(line.quantity ?? "0")} ×{" "}
                              {formatMoney(line.unit_price, currencyCode)}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <aside className="space-y-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <h2 className="mb-4 text-lg font-semibold text-slate-950">Totals</h2>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Subtotal</span>
                    <span className="font-semibold text-slate-900">
                      {formatMoney(invoice.subtotal_amount, currencyCode)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Tax</span>
                    <span className="font-semibold text-slate-900">
                      {formatMoney(invoice.tax_amount, currencyCode)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between border-t border-slate-200 pt-3">
                    <span className="text-slate-700">Total</span>
                    <span className="text-lg font-bold text-slate-950">
                      {formatMoney(invoice.total_amount, currencyCode)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Amount Paid</span>
                    <span className="font-semibold text-slate-900">
                      {formatMoney(invoice.amount_paid, currencyCode)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Amount Due</span>
                    <span className="font-semibold text-rose-700">
                      {formatMoney(invoice.amount_due, currencyCode)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
                <div className="space-y-3">
                  <button
                    type="button"
                    onClick={handleBackToInvoices}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                  >
                    Back to Invoices
                  </button>
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-400"
                  >
                    Record Manual Payment
                  </button>
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-400"
                  >
                    Mark Past Due
                  </button>
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-400"
                  >
                    Download Invoice
                  </button>
                </div>
              </div>
            </aside>
          </div>
        ) : null}
      </div>
    </main>
  );
}
