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
    title: "Support",
    description: "Monitor support workflows and escalation readiness.",
    href: "/dashboard/support",
  },
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

    if ((metrics.loads_needing_review ?? 0) > 0) {
      return "Operational Review Pending";
    }

    return "Stable";
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
            label="Loads in progress"
            value={loading ? "..." : metrics?.loads_total ?? 0}
          />
          <MetricCard
            label="Needs review"
            value={loading ? "..." : metrics?.loads_needing_review ?? 0}
            tone="warning"
          />
          <MetricCard
            label="Pending documents"
            value={loading ? "..." : metrics?.documents_pending_processing ?? 0}
          />
          <MetricCard
            label="Critical issues"
            value={loading ? "..." : metrics?.critical_validation_issues ?? 0}
            tone={
              !loading && (metrics?.critical_validation_issues ?? 0) > 0
                ? "danger"
                : "success"
            }
          />
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