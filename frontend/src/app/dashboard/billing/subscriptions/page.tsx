"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type SubscriptionListItem = {
  id: string;
  customer_account_id?: string | null;
  service_plan_id?: string | null;
  status: string;
  billing_email?: string | null;
  current_period_start?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end?: boolean | null;
};

type SubscriptionListEnvelope = {
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

type SubscriptionListResponse =
  | SubscriptionListEnvelope
  | unknown[]
  | {
      data?: SubscriptionListEnvelope | unknown[];
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

function normalizeSubscriptionListItem(value: unknown): SubscriptionListItem | null {
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
    service_plan_id: normalizeText(record.service_plan_id),
    status: normalizeText(record.status) ?? "unknown",
    billing_email: normalizeText(record.billing_email),
    current_period_start: normalizeText(record.current_period_start),
    current_period_end: normalizeText(record.current_period_end),
    cancel_at_period_end: normalizeBoolean(record.cancel_at_period_end),
  };
}

function isSubscriptionListEnvelope(value: unknown): value is SubscriptionListEnvelope {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isWrappedSubscriptionListResponse(
  value: unknown
): value is { data?: SubscriptionListEnvelope | unknown[]; meta?: ResponseMeta; message?: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    ("data" in value || "message" in value)
  );
}

function normalizeSubscriptionListResponse(payload: SubscriptionListResponse | null): {
  items: SubscriptionListItem[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
} {
  let rawItems: unknown[] = [];
  let meta: ResponseMeta | null = null;

  if (isWrappedSubscriptionListResponse(payload)) {
    if (Array.isArray(payload.data)) {
      rawItems = payload.data;
      meta = payload.meta ?? null;
    } else if (isSubscriptionListEnvelope(payload.data)) {
      rawItems = Array.isArray(payload.data.items) ? payload.data.items : [];
      meta = payload.data;
    }
  } else if (Array.isArray(payload)) {
    rawItems = payload;
  } else if (isSubscriptionListEnvelope(payload)) {
    rawItems = Array.isArray(payload.items) ? payload.items : [];
    meta = payload;
  }

  const items = rawItems
    .map((item) => normalizeSubscriptionListItem(item))
    .filter((item): item is SubscriptionListItem => item !== null);

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

function statusBadge(status: string) {
  switch (status.trim().toLowerCase()) {
    case "active":
      return "bg-emerald-100 text-emerald-800";
    case "cancelled":
      return "bg-slate-200 text-slate-700";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    case "trialing":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-slate-100 text-slate-700";
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

export default function BillingSubscriptionsPage() {
  const [items, setItems] = useState<SubscriptionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);
  const [pages, setPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSubscriptions(): Promise<void> {
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

        const payload = await apiClient.get<SubscriptionListResponse | null>(`/subscriptions?page=${safePage}&page_size=${safePageSize}`, {
          token,
          organizationId,
          signal: controller.signal,
        });

        const normalized = normalizeSubscriptionListResponse(payload);

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
            : "An unexpected error occurred while loading subscriptions."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadSubscriptions();

    return () => {
      controller.abort();
    };
  }, [page, pageSize, reloadKey]);

  const canGoPrevious = page > 1;
  const canGoNext = page < pages;

  function handleRetry(): void {
    setReloadKey((current) => current + 1);
  }

  async function handleCreateSubscription(): Promise<void> {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      return;
    }

    const customerAccountId = window.prompt("Customer account UUID");
    if (!customerAccountId?.trim()) return;
    const servicePlanId = window.prompt("Service plan UUID");
    if (!servicePlanId?.trim()) return;
    const startsAt = window.prompt("Start date/time (ISO)", new Date().toISOString());
    if (!startsAt?.trim()) return;
    const billingEmail = window.prompt("Billing email (optional)", "");

    try {
      setIsCreating(true);
      setErrorMessage(null);
      await apiClient.post(
        "/subscriptions",
        {
          organization_id: organizationId,
          customer_account_id: customerAccountId.trim(),
          service_plan_id: servicePlanId.trim(),
          starts_at: startsAt.trim(),
          billing_email: billingEmail?.trim() || null,
        },
        { token, organizationId }
      );
      handleRetry();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create subscription.");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Billing / Subscriptions
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Subscriptions</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review active customer subscriptions, billing periods, plan assignments, and account
              billing status.
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
              onClick={() => void handleCreateSubscription()}
              disabled={isCreating || isLoading}
              title="Create a minimal operational subscription."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCreating ? "Creating..." : "New Subscription"}
            </button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          {isLoading ? (
            <div className="px-6 py-12 text-sm text-slate-600">Loading subscriptions...</div>
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
              No subscriptions found for this organization.
            </div>
          ) : null}

          {!isLoading && !errorMessage && items.length > 0 ? (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr className="text-left text-slate-600">
                      <th className="px-5 py-4 font-semibold">Subscription</th>
                      <th className="px-5 py-4 font-semibold">Customer</th>
                      <th className="px-5 py-4 font-semibold">Plan</th>
                      <th className="px-5 py-4 font-semibold">Status</th>
                      <th className="px-5 py-4 font-semibold">Billing Email</th>
                      <th className="px-5 py-4 font-semibold">Current Period</th>
                      <th className="px-5 py-4 font-semibold">Cancel at Period End</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {items.map((subscription) => (
                      <tr key={subscription.id} className="hover:bg-slate-50">
                        <td className="px-5 py-4">
                          <div className="font-semibold text-slate-900">{subscription.id}</div>
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {subscription.customer_account_id || "—"}
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {subscription.service_plan_id || "—"}
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                              subscription.status
                            )}`}
                          >
                            {(subscription.status || "unknown").replaceAll("_", " ")}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {subscription.billing_email || "—"}
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {formatDate(subscription.current_period_start)} →{" "}
                          {formatDate(subscription.current_period_end)}
                        </td>
                        <td className="px-5 py-4 text-slate-700">
                          {subscription.cancel_at_period_end ? "Yes" : "No"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-slate-600">
                  Showing page {page} of {pages} · {total} total subscription
                  {total === 1 ? "" : "s"}
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
