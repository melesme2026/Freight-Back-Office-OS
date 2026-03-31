"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useReviewQueue } from "@/hooks/useReviewQueue";

type ReviewQueueRow = {
  load_id: string;
  load_number: string;
  primary_issue: string;
  severity: string;
  issue_count: number;
};

function severityBadge(severity?: string) {
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

function normalizeSeverity(severity?: string): string {
  const normalized = (severity ?? "").trim().toLowerCase();

  if (normalized === "high" || normalized === "medium" || normalized === "low") {
    return normalized;
  }

  return "unknown";
}

function normalizeIssueCount(value: unknown): number {
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

function normalizeReviewQueueItem(item: unknown): ReviewQueueRow | null {
  if (!item || typeof item !== "object") {
    return null;
  }

  const record = item as Record<string, unknown>;
  const loadIdRaw = record.load_id;

  if (typeof loadIdRaw !== "string" || loadIdRaw.trim().length === 0) {
    return null;
  }

  const loadId = loadIdRaw.trim();

  return {
    load_id: loadId,
    load_number:
      typeof record.load_number === "string" && record.load_number.trim().length > 0
        ? record.load_number.trim()
        : "Unknown Load",
    primary_issue:
      typeof record.primary_issue === "string" && record.primary_issue.trim().length > 0
        ? record.primary_issue.trim()
        : "Issue details unavailable",
    severity: normalizeSeverity(
      typeof record.severity === "string" ? record.severity : undefined
    ),
    issue_count: normalizeIssueCount(record.issue_count),
  };
}

export default function ReviewQueuePage() {
  const { reviewQueue, isLoading, error, refetch } = useReviewQueue();

  const normalizedQueue = useMemo<ReviewQueueRow[]>(() => {
    if (!Array.isArray(reviewQueue)) {
      return [];
    }

    return reviewQueue
      .map((item) => normalizeReviewQueueItem(item))
      .filter((item): item is ReviewQueueRow => item !== null);
  }, [reviewQueue]);

  const totalItems = normalizedQueue.length;

  const highSeverityCount = useMemo(() => {
    return normalizedQueue.filter((item) => item.severity === "high").length;
  }, [normalizedQueue]);

  const mediumSeverityCount = useMemo(() => {
    return normalizedQueue.filter((item) => item.severity === "medium").length;
  }, [normalizedQueue]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Review Queue</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Review Queue</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Review loads that require human attention due to missing information, failed
              validation, or low-confidence extraction.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isLoading}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-soft transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Items awaiting review</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : totalItems}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">High severity</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">
              {isLoading ? "..." : highSeverityCount}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Medium severity</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">
              {isLoading ? "..." : mediumSeverityCount}
            </div>
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-rose-800">
                  Unable to load review queue
                </h2>
                <p className="mt-1 text-sm text-rose-700">{error}</p>
              </div>

              <button
                type="button"
                onClick={() => void refetch()}
                className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Load</th>
                  <th className="px-5 py-4 font-semibold">Primary Issue</th>
                  <th className="px-5 py-4 font-semibold">Severity</th>
                  <th className="px-5 py-4 font-semibold">Issue Count</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                      Loading review queue...
                    </td>
                  </tr>
                ) : normalizedQueue.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                      No items currently require review.
                    </td>
                  </tr>
                ) : (
                  normalizedQueue.map((item) => (
                    <tr key={item.load_id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900">{item.load_number}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.load_id}</div>
                      </td>

                      <td className="px-5 py-4 text-slate-700">{item.primary_issue}</td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${severityBadge(
                            item.severity
                          )}`}
                        >
                          {item.severity}
                        </span>
                      </td>

                      <td className="px-5 py-4 font-medium text-slate-900">{item.issue_count}</td>

                      <td className="px-5 py-4">
                        <Link
                          href={`/dashboard/loads/${item.load_id}`}
                          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                        >
                          Review →
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}