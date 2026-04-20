"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getDashboardMetrics, type DashboardMetrics } from "@/lib/dashboard";

const dashboardCards = [
  {
    title: "Loads",
    description: "Track active loads, missing documents, and lifecycle progress.",
    href: "/dashboard/loads",
  },
  {
    title: "Review Queue",
    description: "Resolve validation issues and correct extracted fields.",
    href: "/dashboard/review-queue",
  },
  {
    title: "Billing",
    description: "Review subscriptions, invoices, payments, and account status.",
    href: "/dashboard/billing",
  },
  {
    title: "Customers",
    description: "Manage customer accounts, onboarding, and operational readiness.",
    href: "/dashboard/customers",
  },
  {
    title: "Drivers",
    description: "View drivers, activity, and related paperwork readiness.",
    href: "/dashboard/drivers",
  },
  {
    title: "Brokers",
    description: "Manage broker contacts, MC profiles, and payment terms.",
    href: "/dashboard/brokers",
  },
  {
    title: "Support",
    description: "Monitor support workflows and escalation readiness.",
    href: "/dashboard/support",
  },
] as const;

const OPERATIONAL_QUEUE_DEFS = [
  { key: "missing_documents", label: "Missing Documents", tone: "danger" as const },
  { key: "docs_needs_attention", label: "Docs Need Attention", tone: "warning" as const },
  { key: "ready_to_invoice", label: "Ready to Invoice", tone: "warning" as const },
  { key: "ready_to_submit", label: "Ready to Submit", tone: "warning" as const },
  { key: "submitted_waiting_funding", label: "Submitted Waiting Funding", tone: "default" as const },
  { key: "advance_paid_reserve_pending", label: "Advance Paid / Reserve Pending", tone: "default" as const },
  { key: "payment_overdue", label: "Payment Overdue", tone: "danger" as const },
  { key: "disputed_or_short_paid", label: "Disputed / Short Paid", tone: "danger" as const },
] as const;

function MetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number | string;
  tone?: "default" | "warning" | "danger" | "success";
}) {
  const toneClass =
    tone === "warning"
      ? "text-amber-600"
      : tone === "danger"
        ? "text-rose-600"
        : tone === "success"
          ? "text-emerald-600"
          : "text-slate-950";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-2 text-3xl font-bold ${toneClass}`}>{value}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadDashboard() {
    try {
      setLoading(true);
      setErrorMessage(null);

      const data = await getDashboardMetrics();
      setMetrics(data);
    } catch (error: unknown) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Failed to load dashboard metrics."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const dashboardHealth = useMemo(() => {
    if (!metrics) {
      return "Loading";
    }

    if ((metrics.critical_validation_issues ?? 0) > 0) {
      return "Attention Needed";
    }

    if (
      (metrics.loads_waiting_on_broker ?? 0) > 0 ||
      (metrics.loads_waiting_on_funding ?? 0) > 0
    ) {
      return "Follow-up Pending";
    }

    return "Stable";
  }, [metrics]);

  const actionNow = useMemo(() => {
    if (!metrics) {
      return [];
    }

    const followUpRequired =
      (metrics.loads_ready_to_submit ?? 0) +
      (metrics.loads_waiting_on_broker ?? 0) +
      (metrics.loads_waiting_on_funding ?? 0);
    const agingRisk =
      (metrics.loads_waiting_on_broker ?? 0) +
      (metrics.loads_waiting_on_funding ?? 0);
    const blockedOrReviewNeeded =
      (metrics.loads_needing_review ?? 0) +
      (metrics.critical_validation_issues ?? 0);

    return [
      {
        label: "Follow-up Required",
        value: followUpRequired,
        tone: followUpRequired > 0 ? "warning" : "success",
        helper: "Ready / waiting stages that need operator touches.",
      },
      {
        label: "Overdue / Aging Risk",
        value: agingRisk,
        tone: agingRisk > 0 ? "danger" : "success",
        helper: "Loads sitting with broker/funding pending states.",
      },
      {
        label: "Waiting on Broker",
        value: metrics.loads_waiting_on_broker ?? 0,
        tone: (metrics.loads_waiting_on_broker ?? 0) > 0 ? "warning" : "default",
        helper: "Broker response follow-up queue.",
      },
      {
        label: "Waiting on Funding",
        value: metrics.loads_waiting_on_funding ?? 0,
        tone: (metrics.loads_waiting_on_funding ?? 0) > 0 ? "warning" : "default",
        helper: "Factoring/funding confirmation queue.",
      },
      {
        label: "Ready to Submit",
        value: metrics.loads_ready_to_submit ?? 0,
        tone: (metrics.loads_ready_to_submit ?? 0) > 0 ? "warning" : "default",
        helper: "Prepared loads ready for outbound action.",
      },
      {
        label: "Blocked / Review Needed",
        value: blockedOrReviewNeeded,
        tone: blockedOrReviewNeeded > 0 ? "danger" : "success",
        helper: "Validation-critical or review-stage work.",
      },
    ] as const;
  }, [metrics]);

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Operator Dashboard</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Freight Back Office OS
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Centralize load operations, paperwork review, onboarding, billing, and
              support in one workspace.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Environment
              </div>
              <div className="mt-1 text-sm font-semibold text-slate-900">Local / V1</div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Dashboard Health
              </div>
              <div className="mt-1 text-sm font-semibold text-slate-900">
                {dashboardHealth}
              </div>
            </div>
          </div>
        </header>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-rose-700">{errorMessage}</div>
              <button
                type="button"
                onClick={() => void loadDashboard()}
                className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Ready to Submit"
            value={loading ? "..." : metrics?.loads_ready_to_submit ?? 0}
            tone="warning"
          />
          <MetricCard
            label="Waiting on Broker"
            value={loading ? "..." : metrics?.loads_waiting_on_broker ?? 0}
            tone="warning"
          />
          <MetricCard
            label="Waiting on Funding"
            value={loading ? "..." : metrics?.loads_waiting_on_funding ?? 0}
            tone="warning"
          />
          <MetricCard
            label="Paid"
            value={loading ? "..." : metrics?.loads_paid ?? 0}
            tone="success"
          />
        </section>

        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-950">Action-Now Command Center</h2>
            <p className="mt-1 text-sm text-slate-600">
              Prioritized operational slices so dispatch and billing teams can act quickly.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(loading ? [] : actionNow).map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <MetricCard label={item.label} value={item.value} tone={item.tone} />
                <p className="mt-2 text-xs text-slate-600">{item.helper}</p>
              </div>
            ))}
            {loading ? (
              <div className="text-sm text-slate-500">Loading action-now slices...</div>
            ) : null}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-950">Operational Queues</h2>
            <p className="mt-1 text-sm text-slate-600">
              Click a queue to open filtered loads with the backend-computed next action.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {OPERATIONAL_QUEUE_DEFS.map((queue) => (
              <Link
                key={queue.key}
                href={`/dashboard/loads?queue=${encodeURIComponent(queue.key)}`}
                className="rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50"
              >
                <MetricCard
                  label={queue.label}
                  value={loading ? "..." : metrics?.operational_queues?.[queue.key] ?? 0}
                  tone={queue.tone}
                />
              </Link>
            ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-slate-950">Priority Worklist</h2>
            <p className="mt-1 text-sm text-slate-600">
              Highest-priority loads to move toward funding and payment first.
            </p>
          </div>
          <div className="space-y-3">
            {Object.values(metrics?.queue_load_examples ?? {})
              .flat()
              .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))
              .slice(0, 8)
              .map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">
                        {item.load_number || item.id}
                      </div>
                      <div className="text-xs text-slate-500">
                        {(item.status || "unknown").replaceAll("_", " ")}
                      </div>
                    </div>
                    <div className="text-sm text-slate-700">
                      {item.next_action?.label || "Monitor load"}
                      {item.is_overdue ? (
                        <span className="ml-2 rounded-md bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                          Overdue
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">
                Operational Snapshot
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Use this workspace to move loads through review, document collection,
                submission, funding, and payment without leaving the dashboard.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/dashboard/loads"
                className="inline-flex items-center rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                Open Loads
              </Link>
              <Link
                href="/dashboard/review-queue"
                className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Open Review Queue
              </Link>
            </div>
          </div>
        </section>

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {dashboardCards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">
                    {card.title}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {card.description}
                  </p>
                </div>
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                  Open
                </span>
              </div>
              <div className="mt-5 text-sm font-medium text-brand-700 group-hover:text-brand-800">
                Go to {card.title} →
              </div>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}
