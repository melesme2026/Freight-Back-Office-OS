"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getDashboardMetrics, type DashboardMetrics } from "@/lib/dashboard";
import { getCommandCenter, type CommandCenterData, type Severity } from "@/lib/command-center";
import { getAccessToken } from "@/lib/auth";
import { useLoads, type Load } from "@/hooks/useLoads";

type WorkMode = "dispatcher" | "billing" | "collections";
type OwnershipFilter = "my_follow_ups" | "team_follow_ups" | "unassigned";
type UrgencyLabel = "Overdue" | "Due today" | "Upcoming" | "Unplanned";

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

function parseUserIdFromToken(): string | null {
  const token = getAccessToken();
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = `${base64}${"=".repeat((4 - (base64.length % 4)) % 4)}`;
    const decoded = JSON.parse(atob(padded)) as Record<string, unknown>;
    return typeof decoded.sub === "string" && decoded.sub.trim().length > 0 ? decoded.sub.trim() : null;
  } catch {
    return null;
  }
}

function toStartOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function getUrgency(nextFollowUpAt?: string | null): { label: UrgencyLabel; order: number; tone: "danger" | "warning" | "default"; } {
  if (!nextFollowUpAt) return { label: "Unplanned", order: 4, tone: "default" };
  const parsed = new Date(nextFollowUpAt);
  if (Number.isNaN(parsed.getTime())) return { label: "Unplanned", order: 4, tone: "default" };
  const today = toStartOfDay(new Date());
  const followUpDay = toStartOfDay(parsed);
  const deltaDays = Math.floor((followUpDay.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (deltaDays < 0) return { label: "Overdue", order: 1, tone: "danger" };
  if (deltaDays === 0) return { label: "Due today", order: 2, tone: "warning" };
  return { label: "Upcoming", order: 3, tone: "default" };
}


function severityClasses(severity: Severity): string {
  if (severity === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (severity === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function AIOperationsPanel({ commandCenter }: { commandCenter: CommandCenterData | null }) {
  const assistant = commandCenter?.ai_operations_assistant;
  const recommendations = assistant?.recommendations ?? [];
  const invoiceRisks = assistant?.invoice_risks ?? [];
  const brokerInsights = assistant?.broker_insights ?? [];

  return (
    <section className="mb-8 rounded-2xl border border-indigo-100 bg-white p-4 shadow-soft sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">AI Operations Assistant</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">Deterministic operational intelligence</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">Rules-backed summaries, invoice risk, broker behavior, and collections priorities. The assistant explains why each item appears and does not execute actions automatically.</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {assistant ? "LLM off · rules only" : "Loading assistant..."}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-900">Operational summaries</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {(assistant?.summary ?? []).slice(0, 4).map((item) => (
              <div key={item.id} className={`rounded-xl border p-4 ${severityClasses(item.severity)}`}>
                <div className="text-sm font-semibold">{item.title}</div>
                <div className="mt-2 text-xs leading-5">Recommended: {item.recommendation}</div>
                <details className="mt-2 text-xs">
                  <summary className="cursor-pointer font-semibold">Why</summary>
                  <ul className="mt-2 list-disc space-y-1 pl-4">{item.contributing_factors.map((factor) => <li key={factor}>{factor}</li>)}</ul>
                </details>
              </div>
            ))}
            {!assistant ? <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Loading operational summaries...</div> : null}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Top recommendations</h3>
          <div className="mt-3 space-y-3">
            {recommendations.slice(0, 4).map((item) => (
              <a key={item.id} href={item.href} className={`block rounded-xl border p-4 transition hover:border-brand-300 ${severityClasses(item.severity)}`}>
                <div className="text-sm font-semibold">{item.title}</div>
                <div className="mt-1 text-xs leading-5">{item.description}</div>
                <div className="mt-2 text-xs font-semibold">Why: {item.why}</div>
              </a>
            ))}
            {assistant && recommendations.length === 0 ? <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">No assistant recommendations need action right now.</div> : null}
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Invoice risk visibility</h3>
          <div className="mt-3 space-y-2">
            {invoiceRisks.slice(0, 3).map((item) => (
              <div key={`${item.load_id}:${item.risk_level}`} className="rounded-lg bg-white p-3 text-sm">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <span className="font-semibold text-slate-900">{item.broker_name ?? "Unknown broker"} · {item.invoice_number ?? item.load_number ?? "Invoice"}</span>
                  <span className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white">{item.risk_level}</span>
                </div>
                <div className="mt-1 text-xs text-slate-600">{item.outstanding_amount} outstanding · {item.age_days} days</div>
                <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer font-semibold text-slate-800">Explain risk</summary><ul className="mt-2 list-disc space-y-1 pl-4">{item.risk_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></details>
              </div>
            ))}
            {assistant && invoiceRisks.length === 0 ? <div className="text-sm text-slate-600">No elevated invoice risk in the current command center sample.</div> : null}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Broker behavior insights</h3>
          <div className="mt-3 space-y-2">
            {brokerInsights.slice(0, 3).map((item) => (
              <div key={item.broker_id} className="rounded-lg bg-white p-3 text-sm">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <span className="font-semibold text-slate-900">{item.broker_name}</span>
                  <span className={`rounded-md px-2 py-1 text-xs font-semibold ${item.trend === "worsening" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"}`}>{item.trend}</span>
                </div>
                <div className="mt-1 text-xs text-slate-600">{item.unpaid_invoice_count} unpaid · {item.unpaid_total} open · avg paid cycle {item.average_payment_days ?? "n/a"} days</div>
                <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer font-semibold text-slate-800">Contributing factors</summary><ul className="mt-2 list-disc space-y-1 pl-4">{item.contributing_factors.map((factor) => <li key={factor}>{factor}</li>)}</ul></details>
              </div>
            ))}
            {assistant && brokerInsights.length === 0 ? <div className="text-sm text-slate-600">No elevated broker payment behavior signals in the current command center sample.</div> : null}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
        Explainability: {assistant?.explainability.rules[0] ?? "Assistant output is organization-scoped and generated from existing command center data."}
      </div>
    </section>
  );
}

function isNeedsAttention(load: Load, workMode: WorkMode): boolean {
  const urgency = getUrgency(load.next_follow_up_at);
  const status = (load.status ?? "").toLowerCase();
  const queue = (load.operational?.queue ?? "").toLowerCase();
  const hasMissingDocs = load.has_ratecon !== true || load.has_bol !== true || load.has_invoice !== true;
  if (urgency.order <= 2) return true;
  if (["short_paid", "disputed", "reserve_pending", "advance_paid"].includes(status)) return true;
  if (workMode === "collections" && ["submitted_to_broker", "submitted_to_factoring"].includes(status)) return true;
  if (workMode === "billing" && (status === "invoice_ready" || hasMissingDocs)) return true;
  if (workMode === "dispatcher" && (queue === "missing_documents" || queue === "docs_needs_attention" || hasMissingDocs)) return true;
  return false;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [commandCenter, setCommandCenter] = useState<CommandCenterData | null>(null);
  const { loads } = useLoads();
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [workMode, setWorkMode] = useState<WorkMode>("dispatcher");
  const [ownershipFilter, setOwnershipFilter] = useState<OwnershipFilter>("my_follow_ups");
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(WORK_MODE_STORAGE_KEY);
    if (stored === "dispatcher" || stored === "billing" || stored === "collections") {
      setWorkMode(stored);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(WORK_MODE_STORAGE_KEY, workMode);
  }, [workMode]);

  useEffect(() => {
    setCurrentUserId(parseUserIdFromToken());
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      setErrorMessage(null);
      const [data, commandCenterData] = await Promise.all([getDashboardMetrics(), getCommandCenter()]);
      setMetrics(data);
      setCommandCenter(commandCenterData);
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

  const needsAttentionLoads = useMemo(() => {
    return loads
      .filter((load) => {
        if (!isNeedsAttention(load, workMode)) return false;
        if (ownershipFilter === "unassigned") return !load.follow_up_owner_id;
        if (ownershipFilter === "my_follow_ups") return Boolean(load.follow_up_owner_id && currentUserId && load.follow_up_owner_id === currentUserId);
        return Boolean(load.follow_up_owner_id);
      })
      .sort((a, b) => {
        const urgencyA = getUrgency(a.next_follow_up_at);
        const urgencyB = getUrgency(b.next_follow_up_at);
        if (urgencyA.order !== urgencyB.order) return urgencyA.order - urgencyB.order;
        return (b.operational?.priority_score ?? 0) - (a.operational?.priority_score ?? 0);
      })
      .slice(0, 8);
  }, [loads, workMode, ownershipFilter, currentUserId]);

  return (
    <div className="safe-page px-4 py-6 text-slate-900 sm:px-6 sm:py-10"><div className="mx-auto max-w-7xl">
      <header className="mb-8 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-brand-700">Operator Dashboard</p>
          <h1 className="break-mobile text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Freight Back Office OS</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Centralize load operations, paperwork review, onboarding, billing, and support in one workspace.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft sm:min-w-56">
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
              <button key={mode} type="button" onClick={() => setWorkMode(mode)} className={`touch-target rounded-xl px-4 py-2 text-sm font-semibold transition ${workMode === mode ? "bg-brand-600 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}>
                {workModeConfig[mode].label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 p-4"><div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div className="text-sm text-rose-700">{errorMessage}</div><button type="button" onClick={() => void loadDashboard()} className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700">Retry</button></div></div> : null}

      <AIOperationsPanel commandCenter={commandCenter} />

      <section className={`mb-8 rounded-2xl border p-6 shadow-soft ${workMode === "collections" ? "border-rose-200 bg-rose-50/60" : "border-slate-200 bg-white"}`}>
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Needs Attention</h2>
            <p className="mt-1 text-sm text-slate-600">Start here for urgent follow-up and operational blockers.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {([
              { key: "my_follow_ups", label: "My follow-ups" },
              { key: "team_follow_ups", label: "Team follow-ups" },
              { key: "unassigned", label: "Unassigned" },
            ] as const).map((option) => (
              <button key={option.key} type="button" onClick={() => setOwnershipFilter(option.key)} className={`touch-target rounded-xl px-3 py-2 text-xs font-semibold transition ${ownershipFilter === option.key ? "bg-slate-900 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          {needsAttentionLoads.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">No high-signal items for the selected ownership view.</div>
          ) : (
            needsAttentionLoads.map((load) => {
              const urgency = getUrgency(load.next_follow_up_at);
              return (
                <Link key={load.id} href={`/dashboard/loads/${load.id}`} className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 transition hover:border-brand-300 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">Load {load.load_number ?? load.id.slice(0, 8)}</div>
                    <div className="mt-1 text-xs text-slate-600">{load.operational?.next_action?.label ?? "Follow-up required"} · {(load.operational?.queue ?? "general").replaceAll("_", " ")}</div>
                  </div>
                  <div className="text-left sm:text-right">
                    <span className={`rounded-md px-2 py-1 text-xs font-semibold ${urgency.tone === "danger" ? "bg-rose-100 text-rose-700" : urgency.tone === "warning" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-700"}`}>{urgency.label}</span>
                    <div className="mt-1 text-xs text-slate-500">{load.follow_up_owner_name ?? (load.follow_up_owner_id ? "Assigned" : "Unassigned")}</div>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </section>

      <section className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Ready to Submit" value={loading ? "..." : metrics?.loads_ready_to_submit ?? 0} tone="warning" />
        <MetricCard label="Waiting on Broker" value={loading ? "..." : metrics?.loads_waiting_on_broker ?? 0} tone="warning" />
        <MetricCard label="Waiting on Funding" value={loading ? "..." : metrics?.loads_waiting_on_funding ?? 0} tone="warning" />
        <MetricCard label="Paid" value={loading ? "..." : metrics?.loads_paid ?? 0} tone="success" />
      </section>

      <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
        <h2 className="text-lg font-semibold text-slate-950">Mode Priorities</h2>
        <p className="mt-1 text-sm text-slate-600">Focused KPI slices for the selected work mode.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">{(loading ? [] : modeActionNow).map((item) => <div key={item.label}><MetricCard label={item.label} value={item.value} tone={item.tone as "default"|"warning"|"danger"|"success"} /><p className="mt-2 text-xs text-slate-600">{item.helper}</p></div>)}{loading ? <div className="text-sm text-slate-500">Loading priorities...</div> : null}</div>
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Open Follow-Ups</h3>
              <p className="mt-1 text-xs text-slate-600">Overdue and urgent reminders to keep payment collections moving.</p>
            </div>
            <Link href="/dashboard/follow-ups" className="text-xs font-semibold text-brand-700 hover:underline">View follow-ups</Link>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-md bg-rose-100 px-2 py-1 text-rose-700">Overdue: {metrics?.operational_queues?.payment_overdue ?? 0}</span>
            <span className="rounded-md bg-amber-100 px-2 py-1 text-amber-700">Urgent: {metrics?.operational_queues?.disputed_or_short_paid ?? 0}</span>
          </div>
        </div>
      </section>

      <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
        <div className="mb-4"><h2 className="text-lg font-semibold text-slate-950">Operational Queues</h2><p className="mt-1 text-sm text-slate-600">Queue order follows the selected work mode.</p></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{prioritizedQueues.map((queue) => <Link key={queue.key} href={`/dashboard/loads?queue=${encodeURIComponent(queue.key)}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50"><MetricCard label={queue.label} value={loading ? "..." : metrics?.operational_queues?.[queue.key] ?? 0} tone={queue.tone} /></Link>)}</div>
      </section>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{dashboardCards.map((card) => <Link key={card.title} href={card.href} className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300 sm:p-6"><h2 className="text-lg font-semibold text-slate-950">{card.title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p><div className="mt-5 text-sm font-medium text-brand-700 group-hover:text-brand-800">Go to {card.title} →</div></Link>)}</section>
    </div></div>
  );
}
