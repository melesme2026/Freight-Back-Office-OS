"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getDashboardMetrics, type DashboardMetrics } from "@/lib/dashboard";

type WorkMode = "dispatcher" | "billing" | "collections";

const WORK_MODE_STORAGE_KEY = "dashboard_work_mode";

const workModeConfig: Record<WorkMode, { label: string; helper: string; queuePriority: string[] }> = {
  dispatcher: {
    label: "Dispatcher",
    helper: "Prioritize document collection, newly created loads, and packet blockers.",
    queuePriority: ["missing_documents", "docs_needs_attention", "ready_to_invoice", "disputed_or_short_paid"],
  },
  billing: {
    label: "Billing",
    helper: "Prioritize invoice-ready work, packet completion, and submission throughput.",
    queuePriority: ["ready_to_invoice", "ready_to_submit", "missing_documents", "submitted_waiting_funding"],
  },
  collections: {
    label: "Collections",
    helper: "Prioritize overdue, reserve pending, disputed, and broker/factor follow-up.",
    queuePriority: ["payment_overdue", "disputed_or_short_paid", "advance_paid_reserve_pending", "submitted_waiting_funding"],
  },
};

const dashboardCards = [
  { title: "Loads", description: "Track active loads, missing documents, and lifecycle progress.", href: "/dashboard/loads" },
  { title: "Review Queue", description: "Resolve validation issues and correct extracted fields.", href: "/dashboard/review-queue" },
  { title: "Billing", description: "Track invoice readiness, payment follow-up, and exceptions.", href: "/dashboard/billing" },
  { title: "Customers", description: "Manage customer accounts, onboarding, and operational readiness.", href: "/dashboard/customers" },
  { title: "Drivers", description: "View drivers, activity, and related paperwork readiness.", href: "/dashboard/drivers" },
  { title: "Brokers", description: "Manage broker contacts, MC profiles, and payment terms.", href: "/dashboard/brokers" },
  { title: "Support", description: "Monitor support workflows and escalation readiness.", href: "/dashboard/support" },
] as const;

const OPERATIONAL_QUEUE_DEFS = [
  { key: "missing_documents", label: "Missing Documents", tone: "danger" as const },
  { key: "docs_needs_attention", label: "Docs Need Attention", tone: "warning" as const },
  { key: "ready_to_invoice", label: "Ready to Invoice", tone: "warning" as const },
  { key: "ready_to_submit", label: "Ready to Submit", tone: "warning" as const },
  { key: "submitted_waiting_funding", label: "Awaiting Funding", tone: "default" as const },
  { key: "advance_paid_reserve_pending", label: "Reserve Pending", tone: "default" as const },
  { key: "payment_overdue", label: "Payment Overdue", tone: "danger" as const },
  { key: "disputed_or_short_paid", label: "Disputed / Short Paid", tone: "danger" as const },
] as const;

function MetricCard({ label, value, tone = "default" }: { label: string; value: number | string; tone?: "default" | "warning" | "danger" | "success"; }) {
  const toneClass = tone === "warning" ? "text-amber-600" : tone === "danger" ? "text-rose-600" : tone === "success" ? "text-emerald-600" : "text-slate-950";
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"><div className="text-sm text-slate-500">{label}</div><div className={`mt-2 text-3xl font-bold ${toneClass}`}>{value}</div></div>;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [workMode, setWorkMode] = useState<WorkMode>("dispatcher");

  useEffect(() => {
    const stored = window.localStorage.getItem(WORK_MODE_STORAGE_KEY);
    if (stored === "dispatcher" || stored === "billing" || stored === "collections") {
      setWorkMode(stored);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(WORK_MODE_STORAGE_KEY, workMode);
  }, [workMode]);

  async function loadDashboard() {
    try {
      setLoading(true);
      setErrorMessage(null);
      const data = await getDashboardMetrics();
      setMetrics(data);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const modeActionNow = useMemo(() => {
    if (!metrics) return [];
    if (workMode === "dispatcher") {
      return [
        { label: "Missing Documents", value: metrics.operational_queues?.missing_documents ?? 0, tone: "danger", helper: "Loads blocked on required paperwork." },
        { label: "Docs Need Attention", value: metrics.operational_queues?.docs_needs_attention ?? 0, tone: "warning", helper: "Documents uploaded but require review/fix." },
        { label: "Ready to Invoice", value: metrics.operational_queues?.ready_to_invoice ?? 0, tone: "warning", helper: "Dispatch handoff to billing is ready." },
      ] as const;
    }
    if (workMode === "billing") {
      return [
        { label: "Ready to Invoice", value: metrics.operational_queues?.ready_to_invoice ?? 0, tone: "warning", helper: "Packet ready for invoice generation." },
        { label: "Ready to Submit", value: metrics.loads_ready_to_submit ?? 0, tone: "warning", helper: "Invoices ready for broker/factor submission." },
        { label: "Waiting on Funding", value: metrics.loads_waiting_on_funding ?? 0, tone: "warning", helper: "Submitted loads pending funding confirmation." },
      ] as const;
    }
    return [
      { label: "Payment Overdue", value: metrics.operational_queues?.payment_overdue ?? 0, tone: "danger", helper: "Immediate collection follow-up required." },
      { label: "Disputed / Short Paid", value: metrics.operational_queues?.disputed_or_short_paid ?? 0, tone: "danger", helper: "Dispute and short-pay resolution queue." },
      { label: "Reserve Pending", value: metrics.operational_queues?.advance_paid_reserve_pending ?? 0, tone: "warning", helper: "Reserve release follow-up with factor/broker." },
    ] as const;
  }, [metrics, workMode]);

  const prioritizedQueues = useMemo(() => {
    const priority = workModeConfig[workMode].queuePriority;
    const indexByKey = new Map(priority.map((key, index) => [key, index]));
    return [...OPERATIONAL_QUEUE_DEFS].sort((a, b) => (indexByKey.get(a.key) ?? 99) - (indexByKey.get(b.key) ?? 99));
  }, [workMode]);

  return (
    <div className="px-6 py-10 text-slate-900"><div className="mx-auto max-w-7xl">
      <header className="mb-8 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-brand-700">Operator Dashboard</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Freight Back Office OS</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Centralize load operations, paperwork review, onboarding, billing, and support in one workspace.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
          <div className="text-xs uppercase tracking-wide text-slate-500">Dashboard Health</div>
          <div className="mt-1 text-sm font-semibold text-slate-900">{(metrics?.critical_validation_issues ?? 0) > 0 ? "Attention Needed" : "Operational"}</div>
        </div>
      </header>

      <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Work Mode</h2>
            <p className="mt-1 text-sm text-slate-600">{workModeConfig[workMode].helper}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(["dispatcher", "billing", "collections"] as WorkMode[]).map((mode) => (
              <button key={mode} type="button" onClick={() => setWorkMode(mode)} className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${workMode === mode ? "bg-brand-600 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}>
                {workModeConfig[mode].label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 p-4"><div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div className="text-sm text-rose-700">{errorMessage}</div><button type="button" onClick={() => void loadDashboard()} className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700">Retry</button></div></div> : null}

      <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Ready to Submit" value={loading ? "..." : metrics?.loads_ready_to_submit ?? 0} tone="warning" />
        <MetricCard label="Waiting on Broker" value={loading ? "..." : metrics?.loads_waiting_on_broker ?? 0} tone="warning" />
        <MetricCard label="Waiting on Funding" value={loading ? "..." : metrics?.loads_waiting_on_funding ?? 0} tone="warning" />
        <MetricCard label="Paid" value={loading ? "..." : metrics?.loads_paid ?? 0} tone="success" />
      </section>

      <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h2 className="text-lg font-semibold text-slate-950">Mode Priorities</h2>
        <p className="mt-1 text-sm text-slate-600">Focused KPI slices for the selected work mode.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">{(loading ? [] : modeActionNow).map((item) => <div key={item.label}><MetricCard label={item.label} value={item.value} tone={item.tone as "default"|"warning"|"danger"|"success"} /><p className="mt-2 text-xs text-slate-600">{item.helper}</p></div>)}{loading ? <div className="text-sm text-slate-500">Loading priorities...</div> : null}</div>
      </section>

      <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="mb-4"><h2 className="text-lg font-semibold text-slate-950">Operational Queues</h2><p className="mt-1 text-sm text-slate-600">Queue order follows the selected work mode.</p></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{prioritizedQueues.map((queue) => <Link key={queue.key} href={`/dashboard/loads?queue=${encodeURIComponent(queue.key)}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50"><MetricCard label={queue.label} value={loading ? "..." : metrics?.operational_queues?.[queue.key] ?? 0} tone={queue.tone} /></Link>)}</div>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{dashboardCards.map((card) => <Link key={card.title} href={card.href} className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"><h2 className="text-lg font-semibold text-slate-950">{card.title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p><div className="mt-5 text-sm font-medium text-brand-700 group-hover:text-brand-800">Go to {card.title} →</div></Link>)}</section>
    </div></div>
  );
}
