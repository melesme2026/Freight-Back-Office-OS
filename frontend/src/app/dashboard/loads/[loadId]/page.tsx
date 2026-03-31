"use client";

import { useRouter, useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

type LoadStatus =
  | "new"
  | "docs_received"
  | "extracting"
  | "needs_review"
  | "validated"
  | "ready_to_submit"
  | "submitted"
  | "funded"
  | "paid"
  | "exception"
  | "archived";

type Load = {
  id: string;
  load_number: string | null;
  status: LoadStatus;
  driver_id?: string | null;
  broker_id?: string | null;
  broker_name_raw?: string | null;
  broker_email_raw?: string | null;
  customer_account_id?: string | null;
  pickup_location?: string | null;
  delivery_location?: string | null;
  gross_amount?: number | string | null;
  currency_code?: string | null;
  has_ratecon?: boolean | null;
  has_bol?: boolean | null;
  has_invoice?: boolean | null;
  notes?: string | null;
  last_reviewed_by?: string | null;
  last_reviewed_at?: string | null;
};

type ReviewQueueItem = {
  load_id: string;
  load_number?: string;
  issue_count: number;
  primary_issue?: string;
  severity?: string;
  blocking_issue_count?: number;
  warning_issue_count?: number;
};

type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
  error?: ApiError | null;
};

type StatusTransitionResponse = {
  id: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
};

type MarkReviewedResponse = {
  id: string;
  last_reviewed_by?: string | null;
  last_reviewed_at?: string | null;
  updated_at?: string | null;
};

const NEXT_STATUS_MAP: Partial<Record<LoadStatus, LoadStatus>> = {
  new: "docs_received",
  docs_received: "extracting",
  extracting: "needs_review",
  needs_review: "validated",
  validated: "ready_to_submit",
  ready_to_submit: "submitted",
  submitted: "funded",
  funded: "paid",
};

function statusBadge(status: string) {
  switch (status) {
    case "needs_review":
      return "bg-amber-100 text-amber-800";
    case "validated":
      return "bg-emerald-100 text-emerald-800";
    case "submitted":
      return "bg-blue-100 text-blue-800";
    case "paid":
      return "bg-purple-100 text-purple-800";
    case "docs_received":
      return "bg-cyan-100 text-cyan-800";
    case "extracting":
      return "bg-indigo-100 text-indigo-800";
    case "ready_to_submit":
      return "bg-sky-100 text-sky-800";
    case "funded":
      return "bg-violet-100 text-violet-800";
    case "exception":
      return "bg-rose-100 text-rose-800";
    case "archived":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function issueBadge(severity?: string) {
  switch ((severity ?? "").toLowerCase()) {
    case "high":
      return "bg-rose-100 text-rose-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    case "low":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function formatCurrency(value?: number | string | null, currencyCode = "USD") {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const numericValue = typeof value === "string" ? Number.parseFloat(value) : value;

  if (!Number.isFinite(numericValue)) {
    return String(value);
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode || "USD",
    }).format(numericValue);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(numericValue);
  }
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function getStringField(record: Record<string, unknown> | null, key: string): string | null {
  if (!record) {
    return null;
  }

  const value = record[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function getOptionalBooleanField(
  record: Record<string, unknown> | null,
  key: string
): boolean | null | undefined {
  if (!record || !(key in record)) {
    return undefined;
  }

  const value = record[key];

  if (typeof value === "boolean") {
    return value;
  }

  if (value === null) {
    return null;
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

function getOptionalNumericOrStringField(
  record: Record<string, unknown> | null,
  key: string
): number | string | null | undefined {
  if (!record || !(key in record)) {
    return undefined;
  }

  const value = record[key];

  if (typeof value === "number" || typeof value === "string" || value === null) {
    return value;
  }

  return null;
}

function normalizeLoadStatus(value: unknown): LoadStatus {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";

  switch (normalized) {
    case "new":
    case "docs_received":
    case "extracting":
    case "needs_review":
    case "validated":
    case "ready_to_submit":
    case "submitted":
    case "funded":
    case "paid":
    case "exception":
    case "archived":
      return normalized;
    default:
      return "new";
  }
}

function normalizeSeverity(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const normalized = value.trim().toLowerCase();
  return normalized.length > 0 ? normalized : undefined;
}

function normalizeCount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return Math.floor(value);
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return Math.floor(parsed);
    }
  }

  return 0;
}

function normalizeLoad(payload: unknown): Load | null {
  const record = asRecord(payload);
  const id = getStringField(record, "id");

  if (!id) {
    return null;
  }

  return {
    id,
    load_number: getStringField(record, "load_number"),
    status: normalizeLoadStatus(record?.status),
    driver_id: getStringField(record, "driver_id"),
    broker_id: getStringField(record, "broker_id"),
    broker_name_raw: getStringField(record, "broker_name_raw"),
    broker_email_raw: getStringField(record, "broker_email_raw"),
    customer_account_id: getStringField(record, "customer_account_id"),
    pickup_location: getStringField(record, "pickup_location"),
    delivery_location: getStringField(record, "delivery_location"),
    gross_amount: getOptionalNumericOrStringField(record, "gross_amount"),
    currency_code: getStringField(record, "currency_code"),
    has_ratecon: getOptionalBooleanField(record, "has_ratecon"),
    has_bol: getOptionalBooleanField(record, "has_bol"),
    has_invoice: getOptionalBooleanField(record, "has_invoice"),
    notes: getStringField(record, "notes"),
    last_reviewed_by: getStringField(record, "last_reviewed_by"),
    last_reviewed_at: getStringField(record, "last_reviewed_at"),
  };
}

function normalizeReviewQueueItem(payload: unknown): ReviewQueueItem | null {
  const record = asRecord(payload);
  const loadId = getStringField(record, "load_id");

  if (!loadId) {
    return null;
  }

  return {
    load_id: loadId,
    load_number: getStringField(record, "load_number") ?? undefined,
    issue_count: normalizeCount(record?.issue_count),
    primary_issue: getStringField(record, "primary_issue") ?? undefined,
    severity: normalizeSeverity(record?.severity),
    blocking_issue_count: normalizeCount(record?.blocking_issue_count),
    warning_issue_count: normalizeCount(record?.warning_issue_count),
  };
}

function extractStaffUserId(payload: unknown): string | null {
  const root = asRecord(payload);
  if (!root) {
    return null;
  }

  const directStaffUserId = getStringField(root, "staff_user_id");
  if (directStaffUserId) {
    return directStaffUserId;
  }

  const directId = getStringField(root, "id");
  if (directId) {
    return directId;
  }

  const user = asRecord(root.user);
  const userStaffUserId = getStringField(user, "staff_user_id");
  if (userStaffUserId) {
    return userStaffUserId;
  }

  const userId = getStringField(user, "id");
  if (userId) {
    return userId;
  }

  const staffUser = asRecord(root.staff_user);
  const nestedStaffUserId = getStringField(staffUser, "id");
  if (nestedStaffUserId) {
    return nestedStaffUserId;
  }

  return null;
}

function normalizeLoadIdParam(value: string | string[] | undefined): string | null {
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }

  if (Array.isArray(value) && value.length > 0) {
    const first = value[0];
    if (typeof first === "string" && first.trim().length > 0) {
      return first.trim();
    }
  }

  return null;
}

export default function LoadDetailPage() {
  const router = useRouter();
  const params = useParams<{ loadId: string | string[] }>();
  const loadId = normalizeLoadIdParam(params?.loadId);

  const [load, setLoad] = useState<Load | null>(null);
  const [reviewQueueItem, setReviewQueueItem] = useState<ReviewQueueItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAdvancing, setIsAdvancing] = useState<boolean>(false);
  const [isMarkingReviewed, setIsMarkingReviewed] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchLoad = useCallback(async (): Promise<Load | null> => {
    if (!loadId) {
      return null;
    }

    const token = getAccessToken();

    const response = await apiClient.get<ApiResponse<unknown>>(
      `/api/v1/loads/${encodeURIComponent(loadId)}`,
      {
        token: token ?? undefined,
      }
    );

    return normalizeLoad(response.data);
  }, [loadId]);

  const fetchReviewQueueItem = useCallback(async (): Promise<ReviewQueueItem | null> => {
    if (!loadId) {
      return null;
    }

    const token = getAccessToken();

    const response = await apiClient.get<ApiResponse<unknown>>("/api/v1/review-queue", {
      token: token ?? undefined,
    });

    const items = Array.isArray(response.data) ? response.data : [];

    for (const item of items) {
      const normalized = normalizeReviewQueueItem(item);
      if (normalized && normalized.load_id === loadId) {
        return normalized;
      }
    }

    return null;
  }, [loadId]);

  const fetchCurrentStaffUserId = useCallback(async (): Promise<string> => {
    const token = getAccessToken();

    const response = await apiClient.get<ApiResponse<unknown>>("/api/v1/auth/me", {
      token: token ?? undefined,
    });

    const staffUserId = extractStaffUserId(response.data);

    if (!staffUserId) {
      throw new Error("Unable to determine current staff user ID.");
    }

    return staffUserId;
  }, []);

  const fetchPageData = useCallback(async () => {
    if (!loadId) {
      setLoad(null);
      setReviewQueueItem(null);
      setError("Invalid load identifier.");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const [loadData, reviewItem] = await Promise.all([
        fetchLoad(),
        fetchReviewQueueItem().catch(() => null),
      ]);

      setLoad(loadData);
      setReviewQueueItem(reviewItem);
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : "Failed to fetch load.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [fetchLoad, fetchReviewQueueItem, loadId]);

  useEffect(() => {
    void fetchPageData();
  }, [fetchPageData]);

  const nextStatus = useMemo(() => {
    if (!load) {
      return null;
    }

    return NEXT_STATUS_MAP[load.status] ?? null;
  }, [load]);

  const documents = useMemo(
    () => [
      {
        name: "Rate Confirmation",
        status: load?.has_ratecon ? "received" : "missing",
      },
      {
        name: "Bill of Lading",
        status: load?.has_bol ? "received" : "missing",
      },
      {
        name: "Invoice",
        status: load?.has_invoice ? "received" : "missing",
      },
    ],
    [load]
  );

  const validationIssues = useMemo(() => {
    const issues = new Map<string, string>();

    if (reviewQueueItem?.primary_issue && reviewQueueItem.primary_issue.trim().length > 0) {
      const value = reviewQueueItem.primary_issue.trim();
      issues.set(value.toLowerCase(), value);
    }

    if (load?.has_invoice === false || load?.has_invoice == null) {
      issues.set("invoice missing", "Invoice missing");
    }

    if (load?.has_ratecon === false || load?.has_ratecon == null) {
      issues.set("rate confirmation missing", "Rate confirmation missing");
    }

    if (load?.has_bol === false || load?.has_bol == null) {
      issues.set("bill of lading missing", "Bill of lading missing");
    }

    return Array.from(issues.values());
  }, [load, reviewQueueItem]);

  const totalOpenIssues = useMemo(() => {
    if (reviewQueueItem && reviewQueueItem.issue_count > 0) {
      return reviewQueueItem.issue_count;
    }

    return validationIssues.length;
  }, [reviewQueueItem, validationIssues]);

  async function handleMarkReviewed() {
    if (!load || !loadId || isMarkingReviewed) {
      return;
    }

    try {
      setIsMarkingReviewed(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const staffUserId = await fetchCurrentStaffUserId();

      const query = new URLSearchParams({
        staff_user_id: staffUserId,
      });

      const response = await apiClient.post<ApiResponse<MarkReviewedResponse>>(
        `/api/v1/review-queue/loads/${encodeURIComponent(load.id)}/mark-reviewed?${query.toString()}`,
        undefined,
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();

      const reviewedAt = response.data?.last_reviewed_at;
      const message = reviewedAt
        ? `Load marked as reviewed at ${formatDateTime(reviewedAt)}.`
        : "Load marked as reviewed.";

      setActionMessage(message);
    } catch (caught: unknown) {
      const message =
        caught instanceof Error ? caught.message : "Failed to mark load reviewed.";
      setError(message);
    } finally {
      setIsMarkingReviewed(false);
    }
  }

  async function handleAdvanceStatus() {
    if (!load || !nextStatus || isAdvancing) {
      return;
    }

    try {
      setIsAdvancing(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();

      const query = new URLSearchParams({
        new_status: nextStatus,
        actor_type: "staff_user",
        notes: `Advanced from UI to ${nextStatus}`,
      });

      const response = await apiClient.post<ApiResponse<StatusTransitionResponse>>(
        `/api/v1/loads/${encodeURIComponent(load.id)}/status?${query.toString()}`,
        undefined,
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();

      const resolvedStatus = response.data?.new_status ?? nextStatus;
      setActionMessage(`Status updated to ${resolvedStatus.replaceAll("_", " ")}.`);
    } catch (caught: unknown) {
      const message =
        caught instanceof Error ? caught.message : "Failed to advance status.";
      setError(message);
    } finally {
      setIsAdvancing(false);
    }
  }

  function handleBackToLoads() {
    router.push("/dashboard/loads");
  }

  function handleOpenReviewQueue() {
    router.push("/dashboard/review-queue");
  }

  function handleGoBack() {
    router.back();
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">Loading load...</h1>
            <p className="mt-3 text-sm text-slate-600">
              Fetching load summary, review queue status, and document completeness.
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (error && !load) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">Unable to load load detail</h1>
            <p className="mt-2 text-sm text-rose-700">{error}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleGoBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={handleBackToLoads}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Loads
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!load) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">Load not found</h1>
            <p className="mt-2 text-sm text-rose-700">
              No load matched the requested identifier.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleGoBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={handleBackToLoads}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Loads
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {load.load_number ?? load.id}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Full operational view of a load, including documents, validation issues, and
              workflow progress.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleMarkReviewed}
              disabled={isMarkingReviewed}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isMarkingReviewed ? "Marking..." : "Mark Reviewed"}
            </button>

            <button
              type="button"
              onClick={handleAdvanceStatus}
              disabled={!nextStatus || isAdvancing}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isAdvancing
                ? "Advancing..."
                : nextStatus
                  ? `Advance to ${nextStatus.replaceAll("_", " ")}`
                  : "No Further Status"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {actionMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {actionMessage}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">Load Summary</h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                    load.status
                  )}`}
                >
                  {load.status.replaceAll("_", " ")}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Driver</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.driver_id ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Broker</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.broker_name_raw ?? load.broker_id ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.customer_account_id ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Gross Amount
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatCurrency(load.gross_amount, load.currency_code ?? "USD")}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Pickup</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.pickup_location ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Delivery</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.delivery_location ?? "—"}
                  </div>
                </div>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Last Reviewed By
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.last_reviewed_by ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Last Reviewed At
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(load.last_reviewed_at)}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Documents</h2>
              <div className="space-y-3">
                {documents.map((document) => (
                  <div
                    key={document.name}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-slate-900">{document.name}</div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        document.status === "received"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {document.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-950">Validation Issues</h2>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {totalOpenIssues} open
                  </span>

                  {reviewQueueItem?.severity ? (
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${issueBadge(
                        reviewQueueItem.severity
                      )}`}
                    >
                      {reviewQueueItem.severity}
                    </span>
                  ) : null}
                </div>
              </div>

              {validationIssues.length > 0 ? (
                <div className="space-y-3">
                  {validationIssues.map((issue) => (
                    <div
                      key={issue}
                      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                    >
                      {issue}
                    </div>
                  ))}

                  {reviewQueueItem && reviewQueueItem.issue_count > validationIssues.length ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                      Additional unresolved validation items exist for this load. Open Review Queue
                      for the current review summary.
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-sm text-slate-500">No open validation issues.</div>
              )}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={handleOpenReviewQueue}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Review Queue
                </button>
                <button
                  type="button"
                  onClick={handleBackToLoads}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Back to Loads
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Notes</h2>
              <div className="text-sm text-slate-700">
                {load.notes && load.notes.trim().length > 0 ? load.notes : "No notes available."}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}