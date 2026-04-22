"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type ServicePlanListItem = {
  id: string;
  name: string;
  code: string;
  billing_cycle?: string | null;
  base_price?: string | number | null;
  per_load_price?: string | number | null;
  per_driver_price?: string | number | null;
  currency_code?: string | null;
  is_active?: boolean | null;
};

type ServicePlanListEnvelope = {
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

type ServicePlanListResponse =
  | ServicePlanListEnvelope
  | unknown[]
  | {
      data?: ServicePlanListEnvelope | unknown[];
      meta?: ResponseMeta;
      message?: string;
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

function normalizeBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "number") {
    if (value === 1) {
      return true;
    }
    if (value === 0) {
      return false;
    }
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1" || normalized === "yes") {
      return true;
    }
    if (normalized === "false" || normalized === "0" || normalized === "no") {
      return false;
    }
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

function normalizeServicePlanListItem(value: unknown): ServicePlanListItem | null {
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
    name: normalizeText(record.name) ?? "Unnamed Plan",
    code: normalizeText(record.code) ?? "—",
    billing_cycle: normalizeText(record.billing_cycle),
    base_price: normalizeNumberLike(record.base_price),
    per_load_price: normalizeNumberLike(record.per_load_price),
    per_driver_price: normalizeNumberLike(record.per_driver_price),
    currency_code: normalizeText(record.currency_code) ?? "USD",
    is_active: normalizeBoolean(record.is_active),
  };
}

function isServicePlanListEnvelope(value: unknown): value is ServicePlanListEnvelope {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isWrappedServicePlanListResponse(
  value: unknown
): value is { data?: ServicePlanListEnvelope | unknown[]; meta?: ResponseMeta; message?: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    ("data" in value || "message" in value)
  );
}

function normalizeServicePlanListResponse(payload: ServicePlanListResponse | null): {
  items: ServicePlanListItem[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
} {
  let rawItems: unknown[] = [];
  let meta: ResponseMeta | null = null;

  if (isWrappedServicePlanListResponse(payload)) {
    if (Array.isArray(payload.data)) {
      rawItems = payload.data;
      meta = payload.meta ?? null;
    } else if (isServicePlanListEnvelope(payload.data)) {
      rawItems = Array.isArray(payload.data.items) ? payload.data.items : [];
      meta = payload.data;
    }
  } else if (Array.isArray(payload)) {
    rawItems = payload;
  } else if (isServicePlanListEnvelope(payload)) {
    rawItems = Array.isArray(payload.items) ? payload.items : [];
    meta = payload;
  }

  const items = rawItems
    .map((item) => normalizeServicePlanListItem(item))
    .filter((item): item is ServicePlanListItem => item !== null);

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

function formatMoney(value: string | number | null | undefined, currencyCode?: string | null): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numeric = Number(value);
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

function formatBillingCycle(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return value.replaceAll("_", " ");
}

export default function BillingPlansPage() {
  const [items, setItems] = useState<ServicePlanListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);
  const [pages, setPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPlans(): Promise<void> {
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

        const payload = await apiClient.get<ServicePlanListResponse | null>(`/service-plans?page=${safePage}&page_size=${safePageSize}`, {
          token,
          organizationId,
          signal: controller.signal,
        });

        const normalized = normalizeServicePlanListResponse(payload);

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
            : "An unexpected error occurred while loading service plans."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadPlans();

    return () => {
      controller.abort();
    };
  }, [page, pageSize, reloadKey]);

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
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Plans</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Service Plans</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage pricing plans, billing cadence, and usage pricing for customer subscriptions.
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
              title="Plan creation is disabled in this workspace."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              New Plan (Unavailable)
            </button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          {isLoading ? (
            <div className="px-6 py-12 text-sm text-slate-600">Loading service plans...</div>
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
              No service plans found for this organization.
            </div>
          ) : null}

          {!isLoading && !errorMessage && items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-slate-600">
                      <th className="px-5 py-4 font-semibold">Plan</th>
                      <th className="px-5 py-4 font-semibold">Code</th>
                      <th className="px-5 py-4 font-semibold">Billing Cycle</th>
                      <th className="px-5 py-4 font-semibold">Base Price</th>
                      <th className="px-5 py-4 font-semibold">Per Load</th>
                      <th className="px-5 py-4 font-semibold">Per Driver</th>
                      <th className="px-5 py-4 font-semibold">Status</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {items.map((plan) => (
                      <tr key={plan.id} className="hover:bg-slate-50">
                        <td className="px-5 py-4">
                          <div className="font-semibold text-slate-900">{plan.name || "—"}</div>
                          <div className="text-xs text-slate-500">{plan.id}</div>
                        </td>

                        <td className="px-5 py-4 text-slate-700">{plan.code || "—"}</td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatBillingCycle(plan.billing_cycle)}
                        </td>

                        <td className="px-5 py-4 font-medium text-slate-900">
                          {formatMoney(plan.base_price, plan.currency_code)}
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatMoney(plan.per_load_price, plan.currency_code)}
                        </td>

                        <td className="px-5 py-4 text-slate-700">
                          {formatMoney(plan.per_driver_price, plan.currency_code)}
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                              plan.is_active
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-slate-200 text-slate-700"
                            }`}
                          >
                            {plan.is_active ? "active" : "inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-slate-600">
                  Showing page {page} of {pages} · {total} total plan{total === 1 ? "" : "s"}
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
