"use client";

import Link from "next/link";
import type { Route } from "next";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { normalizeApiError } from "@/lib/api-client";
import { getCommandCenter, type CollectionItem, type CommandCenterAlert, type CommandCenterData, type CommandCenterTask, type MissingDocItem, type Severity } from "@/lib/command-center";

function formatCurrency(value: string | number | null | undefined): string {
  const amount = Number(value ?? 0);
  if (Number.isNaN(amount)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function severityClasses(severity: Severity): string {
  if (severity === "critical") return "border-rose-200 bg-rose-50 text-rose-700";
  if (severity === "warning") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-sky-200 bg-sky-50 text-sky-700";
}

function asRoute(href: string): Route {
  return href as Route;
}

function severityDot(severity: Severity): string {
  if (severity === "critical") return "bg-rose-500";
  if (severity === "warning") return "bg-amber-500";
  return "bg-sky-500";
}

function KpiCard({ label, value, helper, severity = "info" }: { label: string; value: string | number; helper: string; severity?: Severity }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`h-2.5 w-2.5 rounded-full ${severityDot(severity)}`} aria-hidden="true" />
      </div>
      <div className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</div>
      <p className="mt-2 text-xs leading-5 text-slate-500">{helper}</p>
    </div>
  );
}

function SectionShell({ title, subtitle, action, children }: { title: string; subtitle: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white shadow-soft">
      <div className="flex flex-col gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function PriorityCards({ data }: { data: CommandCenterData }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {data.priority_cards.map((card) => (
        <div key={card.key} className={`rounded-2xl border p-5 ${severityClasses(card.severity)}`}>
          <p className="text-sm font-semibold">{card.label}</p>
          <div className="mt-3 text-4xl font-bold">{card.count}</div>
          <p className="mt-3 text-sm leading-5 opacity-90">{card.next_action}</p>
        </div>
      ))}
    </div>
  );
}

function AlertsPanel({ alerts }: { alerts: CommandCenterAlert[] }) {
  if (alerts.length === 0) {
    return <p className="rounded-2xl border border-dashed border-slate-200 p-5 text-sm text-slate-500">No operational alerts right now.</p>;
  }

  return (
    <div className="space-y-3">
      {alerts.slice(0, 10).map((alert) => (
        <Link key={alert.id} href={asRoute(alert.href)} className="block rounded-2xl border border-slate-200 p-4 transition hover:border-slate-300 hover:bg-slate-50">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClasses(alert.severity)}`}>{formatLabel(alert.severity)}</span>
                <span className="text-xs font-medium text-slate-500">Priority {alert.priority_score}</span>
              </div>
              <h3 className="mt-2 font-semibold text-slate-950">{alert.title}</h3>
              <p className="mt-1 text-sm leading-5 text-slate-600">{alert.description}</p>
            </div>
            <div className="shrink-0 text-sm font-medium text-slate-500">{alert.load_number ?? "Load"}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}

function MissingDocsPanel({ items }: { items: MissingDocItem[] }) {
  return (
    <div className="mobile-scroll-area overflow-x-auto">
      <table className="min-w-[880px] divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Load</th>
            <th className="px-3 py-3">Lane</th>
            <th className="px-3 py-3">Missing / blocker</th>
            <th className="px-3 py-3">Status</th>
            <th className="px-3 py-3">Priority</th>
            <th className="px-3 py-3">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {items.length === 0 ? (
            <tr><td colSpan={6} className="px-3 py-4 text-slate-500">No missing required document bottlenecks.</td></tr>
          ) : items.map((item) => (
            <tr key={item.load_id}>
              <td className="px-3 py-3 font-medium text-slate-950">
                {item.load_number ?? "—"}
                <div className="text-xs font-normal text-slate-500">{item.driver_name ?? "No driver"} · {item.broker_name ?? "No broker"}</div>
              </td>
              <td className="max-w-[260px] px-3 py-3 text-slate-600">{item.lane}</td>
              <td className="px-3 py-3 text-slate-600">
                <div>{item.missing_required_documents.length ? item.missing_required_documents.map(formatLabel).join(", ") : "No required docs missing"}</div>
                {item.unresolved_blockers.length ? <div className="mt-1 text-xs text-rose-600">{item.unresolved_blockers.length} packet intelligence blocker(s)</div> : null}
              </td>
              <td className="px-3 py-3 text-slate-600">{formatLabel(item.status)}</td>
              <td className="px-3 py-3"><span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClasses(item.severity)}`}>{item.priority_score}</span></td>
              <td className="px-3 py-3"><Link href={asRoute(`/dashboard/loads/${item.load_id}`)} className="font-semibold text-blue-600 hover:text-blue-700">Open load</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CollectionsPanel({ items }: { items: CollectionItem[] }) {
  return (
    <div className="space-y-3">
      {items.length === 0 ? <p className="rounded-2xl border border-dashed border-slate-200 p-5 text-sm text-slate-500">No urgent unpaid collections items.</p> : items.slice(0, 8).map((item) => (
        <div key={`${item.load_id}-${item.payment_status}`} className="rounded-2xl border border-slate-200 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClasses(item.severity)}`}>{formatLabel(item.severity)}</span>
                <span className="text-xs font-medium text-slate-500">{item.age_days} days</span>
              </div>
              <h3 className="mt-2 font-semibold text-slate-950">{item.load_number ?? "Load"} · {item.invoice_number ?? "No invoice #"}</h3>
              <p className="mt-1 text-sm text-slate-600">{item.broker_name ?? "No broker"} · {item.lane}</p>
              <p className="mt-2 text-xs leading-5 text-slate-500">{item.reason}</p>
            </div>
            <div className="text-left sm:text-right">
              <div className="text-xl font-bold text-slate-950">{formatCurrency(item.outstanding_amount)}</div>
              <div className="text-xs text-slate-500">{formatLabel(item.payment_status)}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function TaskCenter({ tasks }: { tasks: CommandCenterTask[] }) {
  const grouped = useMemo(() => ({
    critical: tasks.filter((task) => task.severity === "critical"),
    warning: tasks.filter((task) => task.severity === "warning"),
    info: tasks.filter((task) => task.severity === "info"),
  }), [tasks]);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {(["critical", "warning", "info"] as Severity[]).map((severity) => (
        <div key={severity} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{formatLabel(severity)}</h3>
          <div className="mt-3 space-y-3">
            {grouped[severity].length === 0 ? <p className="text-sm text-slate-500">No {severity} tasks.</p> : grouped[severity].slice(0, 6).map((task) => (
              <Link href={asRoute(task.href)} key={task.id} className="block rounded-xl bg-white p-3 shadow-sm ring-1 ring-slate-100 transition hover:ring-slate-300">
                <div className="font-semibold text-slate-950">{task.title}</div>
                <div className="mt-1 text-xs text-slate-500">{task.load_number ?? "Load"} · Priority {task.priority_score}</div>
                <p className="mt-2 text-sm leading-5 text-slate-600">{task.description}</p>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; requestId?: string; retryable: boolean } | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getCommandCenter();
      setData(response);
    } catch (err: unknown) {
      const normalized = normalizeApiError(err, "Command center is temporarily unavailable. Retry or use the load, billing, and document workspaces directly.");
      setError({ message: normalized.message, requestId: normalized.requestId, retryable: normalized.retryable });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell title="Dispatcher Command Center" subtitle="Prioritized freight operations workspace for missing docs, blocked packets, urgent collections, factoring reserves, and daily dispatcher tasks.">
      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading command center…</div> : null}
      {error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-semibold">Command center is unavailable right now.</p>
              <p className="mt-1">{error.message}</p>
              {error.requestId ? <p className="mt-2 text-xs text-amber-700">Support reference: {error.requestId}</p> : null}
            </div>
            <button type="button" onClick={() => void load()} className="touch-target rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white">Retry</button>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <Link href="/dashboard/loads" className="rounded-xl bg-white px-4 py-3 font-semibold text-slate-800 ring-1 ring-amber-100">Open loads</Link>
            <Link href="/dashboard/documents" className="rounded-xl bg-white px-4 py-3 font-semibold text-slate-800 ring-1 ring-amber-100">Open documents</Link>
            <Link href="/dashboard/billing" className="rounded-xl bg-white px-4 py-3 font-semibold text-slate-800 ring-1 ring-amber-100">Open billing</Link>
          </div>
        </div>
      ) : null}
      {data ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Active loads" value={data.kpis.active_loads} helper="Open freight operations excluding archived and fully paid loads." />
            <KpiCard label="Loads missing docs" value={data.kpis.loads_missing_docs} helper="Required packet documents missing from active loads." severity={data.kpis.loads_missing_docs > 0 ? "warning" : "info"} />
            <KpiCard label="Overdue invoices" value={data.kpis.overdue_invoices} helper="Unpaid balances older than 30 days from operational reference date." severity={data.kpis.overdue_invoices > 0 ? "critical" : "info"} />
            <KpiCard label="Unpaid total" value={formatCurrency(data.kpis.unpaid_total)} helper="Outstanding amount across scoped operational payment records." severity={Number(data.kpis.unpaid_total) > 0 ? "warning" : "info"} />
            <KpiCard label="Pending packet sends" value={data.kpis.pending_packet_sends} helper="Draft, ready, or queued billing packets requiring action." />
            <KpiCard label="Packet blockers" value={data.kpis.unresolved_packet_intelligence_blockers} helper="Unresolved blocking validation findings." severity={data.kpis.unresolved_packet_intelligence_blockers > 0 ? "critical" : "info"} />
            <KpiCard label="Reserve pending" value={data.kpis.factoring_reserve_pending} helper={`${formatCurrency(data.kpis.factoring_reserve_pending_total)} still pending release.`} severity={data.kpis.factoring_reserve_pending > 0 ? "warning" : "info"} />
            <KpiCard label="Urgent collections" value={data.kpis.urgent_collections} helper="High-priority receivables based on deterministic aging/status logic." severity={data.kpis.urgent_collections > 0 ? "critical" : "info"} />
          </div>

          <PriorityCards data={data} />

          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <SectionShell title="Operational alerts" subtitle="Explainable alerts for missing PODs, blocked packets, stale load activity, factoring issues, and overdue invoices.">
              <AlertsPanel alerts={data.alerts} />
            </SectionShell>
            <SectionShell title="Urgent collections" subtitle={`${data.collections.summary.urgent_count} urgent · ${formatCurrency(data.collections.summary.unpaid_total)} unpaid · ${formatCurrency(data.collections.summary.reserve_pending_total)} reserve pending`}>
              <CollectionsPanel items={data.collections.items} />
            </SectionShell>
          </div>

          <SectionShell title="Missing-doc heatmap" subtitle={`${data.missing_docs.summary.total_loads} loads missing required docs or blocked from packet send. Document groups: ${Object.entries(data.missing_docs.summary.by_document_type).map(([key, value]) => `${formatLabel(key)} ${value}`).join(" · ") || "none"}`}>
            <MissingDocsPanel items={data.missing_docs.items} />
          </SectionShell>

          <SectionShell title="Daily task center" subtitle={`${data.tasks.summary.total} deterministic operational tasks grouped by urgency for dispatcher follow-through.`} action={<span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">No AI scoring · no GPS tracking</span>}>
            <TaskCenter tasks={data.tasks.items} />
          </SectionShell>

          <SectionShell title="Recent operational activity" subtitle="Latest scoped audit events for context while working the command center.">
            {data.recent_activity.length === 0 ? <p className="text-sm text-slate-500">No recent activity recorded.</p> : (
              <div className="space-y-2">
                {data.recent_activity.map((item) => (
                  <div key={item.id} className="flex flex-col rounded-xl border border-slate-100 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                    <span className="font-medium text-slate-800">{formatLabel(item.entity_type)} · {formatLabel(item.action)}</span>
                    <span className="text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </SectionShell>
        </div>
      ) : null}
    </AppShell>
  );
}
