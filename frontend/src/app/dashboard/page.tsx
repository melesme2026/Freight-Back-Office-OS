"use client";

import Link from "next/link";
import type { Route } from "next";
import { useEffect, useMemo, useState } from "react";

import { normalizeApiError } from "@/lib/api-client";
import { getDashboardMetrics, type DashboardMetrics } from "@/lib/dashboard";
import { getCommandCenter, type CommandCenterData, type Severity } from "@/lib/command-center";
import { useLoads, type Load } from "@/hooks/useLoads";

type WorkMode = "dispatcher" | "billing" | "collections";
type Tone = "default" | "warning" | "danger" | "success";
type DashboardHref = Route;
type KpiCardProps = { label: string; value: number | string; helper: string; tone?: Tone; href?: DashboardHref };

const WORK_MODE_STORAGE_KEY = "dashboard_work_mode";

const workModeConfig: Record<WorkMode, { label: string; helper: string }> = {
  dispatcher: { label: "Dispatch", helper: "Collect paperwork and keep active loads moving." },
  billing: { label: "Billing", helper: "Package invoice-ready loads and clear submission blockers." },
  collections: { label: "Collections", helper: "Work overdue payments, exceptions, and follow-ups." },
};

const quickAccess = [
  { title: "Loads", href: "/dashboard/loads", helper: "Active freight" },
  { title: "Billing", href: "/dashboard/billing", helper: "Invoice work" },
  { title: "Drivers", href: "/dashboard/drivers", helper: "Driver coordination" },
  { title: "Documents", href: "/dashboard/documents", helper: "Paperwork intake" },
  { title: "Review Queue", href: "/dashboard/review-queue", helper: "Fix exceptions" },
] as const;

const emptyStateActions = [
  { title: "Create first load", href: "/dashboard/loads/new", helper: "Start the operating workflow with pickup, delivery, broker, and driver details." },
  { title: "Upload first document", href: "/dashboard/documents", helper: "Add a rate confirmation, BOL, POD, or invoice to begin packet readiness tracking." },
  { title: "Invite first driver", href: "/dashboard/drivers/new", helper: "Connect drivers to load updates and mobile document capture." },
  { title: "Complete carrier profile", href: "/dashboard/settings/carrier-profile", helper: "Add remit-to and company details before invoices or packets go out." },
] as const;

function toneClasses(tone: Tone): string {
  if (tone === "danger") return "text-rose-700 bg-rose-50 border-rose-100";
  if (tone === "warning") return "text-amber-700 bg-amber-50 border-amber-100";
  if (tone === "success") return "text-emerald-700 bg-emerald-50 border-emerald-100";
  return "text-slate-900 bg-white border-slate-200";
}

function severityClasses(severity: Severity): string {
  if (severity === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (severity === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function SkeletonBlock({ className = "h-20" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton rounded-2xl bg-slate-200/80 ${className}`} />;
}

function isDashboardHref(href: string): href is DashboardHref {
  return href.startsWith("/dashboard/") || href === "/dashboard";
}

function KpiCard({ label, value, helper, tone = "default", href }: KpiCardProps) {
  const body = (
    <div className={`h-full rounded-2xl border p-4 shadow-sm transition ${toneClasses(tone)} ${href ? "hover:-translate-y-0.5 hover:border-brand-300" : ""}`}>
      <div className="text-xs font-bold uppercase tracking-[0.12em] opacity-70">{label}</div>
      <div className="mt-3 text-3xl font-bold tracking-tight">{value}</div>
      <div className="mt-2 text-xs leading-5 opacity-75">{helper}</div>
    </div>
  );

  return href ? <Link href={href}>{body}</Link> : body;
}

function CommandHeader({ metrics, workMode, setWorkMode, refreshing }: { metrics: DashboardMetrics | null; workMode: WorkMode; setWorkMode: (mode: WorkMode) => void; refreshing: boolean }) {
  const criticalIssues = metrics?.critical_validation_issues ?? 0;
  const health = criticalIssues > 0 ? "Attention needed" : "Operational";

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-brand-700">Command Center</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Today’s freight back-office control room</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">A focused view of paperwork blockers, invoice readiness, submissions, payments, and follow-ups.</p>
        </div>
        <div className="grid gap-3 sm:min-w-[24rem] sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">System state</div>
            <div className="mt-2 flex items-center gap-2 text-sm font-semibold text-slate-950"><span className={`h-2.5 w-2.5 rounded-full ${criticalIssues > 0 ? "bg-amber-500" : "bg-emerald-500"}`} />{health}</div>
            <div className="mt-1 text-xs text-slate-500">{refreshing ? "Refreshing quietly" : "Live workspace"}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Active loads</div>
            <div className="mt-2 text-2xl font-bold text-slate-950">{metrics?.loads_total ?? 0}</div>
            <div className="mt-1 text-xs text-slate-500">{metrics?.loads_paid ?? 0} paid</div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-slate-100 pt-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-950">Work mode</div>
          <p className="mt-1 text-sm text-slate-600">{workModeConfig[workMode].helper}</p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Select work mode">
          {(["dispatcher", "billing", "collections"] as WorkMode[]).map((mode) => (
            <button key={mode} type="button" onClick={() => setWorkMode(mode)} className={`touch-target rounded-xl px-4 py-2 text-sm font-semibold transition focus-visible:ring-2 focus-visible:ring-brand-500 ${workMode === mode ? "bg-slate-950 text-white" : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}>
              {workModeConfig[mode].label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function isPriorityLoad(load: Load, workMode: WorkMode): boolean {
  const queues = new Set([load.operational?.queue, ...(load.operational?.queues ?? [])].filter(Boolean));
  if (workMode === "collections") return queues.has("payment_overdue") || queues.has("disputed_or_short_paid") || Boolean(load.follow_up_required);
  if (workMode === "billing") return queues.has("ready_to_invoice") || queues.has("ready_to_submit") || queues.has("missing_documents");
  return queues.has("missing_documents") || queues.has("docs_needs_attention") || Boolean(load.follow_up_required);
}

function OperationalIntelligencePanel({ commandCenter, isLoading }: { commandCenter: CommandCenterData | null; isLoading: boolean }) {
  const intelligence = commandCenter?.operational_intelligence;
  const needsAttention = intelligence?.needs_attention ?? [];
  const readiness = intelligence?.readiness.items ?? [];
  const followUps = intelligence?.follow_ups.items ?? [];
  const driverGaps = intelligence?.driver_visibility.items ?? [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand-700">Operational intelligence</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">Needs-attention command center</h2>
          <p className="mt-1 text-sm text-slate-600">Rules-backed readiness, follow-up urgency, stalled-load, driver, and validation signals. No AI actions or invoice math changes.</p>
        </div>
        {intelligence ? (
          <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{intelligence.summary.needs_attention_count} items to triage</span>
        ) : null}
      </div>

      {!intelligence && isLoading ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-4">
          <SkeletonBlock className="h-28" />
          <SkeletonBlock className="h-28" />
          <SkeletonBlock className="h-28" />
          <SkeletonBlock className="h-28" />
        </div>
      ) : null}

      {intelligence ? (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Needs Attention" value={intelligence.summary.needs_attention_count} helper="Blocking alerts, stale work, and due follow-ups" tone={intelligence.summary.needs_attention_count > 0 ? "danger" : "success"} />
            <KpiCard label="Ready Revenue" value={intelligence.summary.ready_to_submit_count} helper="Loads ready to submit or invoice" tone="success" />
            <KpiCard label="Stalled Loads" value={intelligence.summary.stalled_load_count} helper="No operational update past threshold" tone={intelligence.summary.stalled_load_count > 0 ? "warning" : "default"} />
            <KpiCard label="Driver Gaps" value={intelligence.summary.driver_gap_count} helper="Active driver profiles missing contact items" tone={intelligence.summary.driver_gap_count > 0 ? "warning" : "default"} />
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-bold text-slate-950">Work first</h3>
                <span className="text-xs font-semibold text-slate-500">Priority ordered</span>
              </div>
              <div className="mt-3 space-y-3">
                {needsAttention.slice(0, 5).map((item) => {
                  const href = isDashboardHref(item.href) ? item.href : "/dashboard";
                  return (
                    <Link key={`${item.source}:${item.id ?? item.load_id ?? item.title}`} href={href} className={`block rounded-2xl border p-4 transition hover:bg-white ${severityClasses(item.severity)}`}>
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="text-sm font-bold">{item.title ?? "Operational follow-up"}</div>
                          <p className="mt-1 text-xs leading-5">{item.next_action ?? item.description ?? "Review this workflow before it blocks revenue movement."}</p>
                        </div>
                        <span className="w-fit rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.08em]">{item.source.replaceAll("_", " ")}</span>
                      </div>
                    </Link>
                  );
                })}
                {needsAttention.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-600">No elevated needs-attention items found.</div> : null}
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <h3 className="text-sm font-bold text-slate-950">Readiness snapshot</h3>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-xl bg-white p-3"><div className="font-bold text-slate-950">{intelligence.readiness.summary.ready_to_invoice}</div><div className="text-slate-500">ready to invoice</div></div>
                  <div className="rounded-xl bg-white p-3"><div className="font-bold text-slate-950">{intelligence.readiness.summary.blocked_packet_submission}</div><div className="text-slate-500">packet blocked</div></div>
                </div>
                <div className="mt-3 space-y-2">
                  {readiness.slice(0, 3).map((item) => {
                    const href = isDashboardHref(item.href) ? item.href : "/dashboard/loads";
                    return <Link key={item.load_id} href={href} className="block rounded-xl bg-white p-3 text-xs text-slate-600 ring-1 ring-slate-200"><span className="font-bold text-slate-950">{item.load_number ?? item.load_id.slice(0, 8)}</span> · {item.next_action}</Link>;
                  })}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <h3 className="text-sm font-bold text-slate-950">Follow-up urgency</h3>
                <p className="mt-1 text-xs text-slate-500">{intelligence.follow_ups.summary.overdue} overdue · {intelligence.follow_ups.summary.stale} stale · {intelligence.follow_ups.summary.due_today} due today</p>
                <div className="mt-3 space-y-2">
                  {followUps.slice(0, 2).map((item) => <Link key={item.id} href="/dashboard/follow-ups" className="block rounded-xl bg-white p-3 text-xs text-slate-600 ring-1 ring-slate-200"><span className="font-bold text-slate-950">{item.title}</span> · {item.urgency.replaceAll("_", " ")}</Link>)}
                  {driverGaps.slice(0, 1).map((item) => {
                    const href = isDashboardHref(item.href) ? item.href : "/dashboard/drivers";
                    return <Link key={item.driver_id} href={href} className="block rounded-xl bg-white p-3 text-xs text-slate-600 ring-1 ring-slate-200"><span className="font-bold text-slate-950">{item.driver_name}</span> missing {item.missing_items.join(", ")}</Link>;
                  })}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

function ActivePriorities({ loads, workMode, isLoading }: { loads: Load[]; workMode: WorkMode; isLoading: boolean }) {
  const priorityLoads = useMemo(() => loads.filter((load) => isPriorityLoad(load, workMode)).slice(0, 5), [loads, workMode]);

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-950">Active priorities</h2>
          <p className="mt-1 text-sm text-slate-600">The next operational decisions to clear blockers and protect cash flow.</p>
        </div>
        <Link href="/dashboard/follow-ups" className="text-sm font-semibold text-brand-700 hover:text-brand-800">View follow-ups →</Link>
      </div>

      <div className="mt-5 space-y-3">
        {isLoading && priorityLoads.length === 0 ? (
          <>
            <SkeletonBlock className="h-16" />
            <SkeletonBlock className="h-16" />
            <SkeletonBlock className="h-16" />
          </>
        ) : null}
        {!isLoading && priorityLoads.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
            No urgent blockers are assigned to this mode. Use quick access below to create a load, collect documents, or review exceptions.
          </div>
        ) : null}
        {priorityLoads.map((load) => (
          <Link key={load.id} href={`/dashboard/loads/${load.id}`} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 transition hover:border-brand-300 hover:bg-white sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-bold text-slate-950">Load {load.load_number ?? load.id.slice(0, 8)}</div>
              <div className="mt-1 text-xs text-slate-600">{load.operational?.next_action?.label ?? "Next follow-up required"} · {(load.operational?.queue ?? "operations").replaceAll("_", " ")}</div>
            </div>
            <span className="w-fit rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">{load.follow_up_owner_name ?? (load.follow_up_owner_id ? "Assigned" : "Unassigned")}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function SecondaryIntelligence({ commandCenter }: { commandCenter: CommandCenterData | null }) {
  const assistant = commandCenter?.ai_operations_assistant;
  const insights = assistant?.summary ?? [];
  const recommendations = assistant?.recommendations ?? [];
  const invoiceRisks = assistant?.invoice_risks ?? [];
  const brokerInsights = assistant?.broker_insights ?? [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Rules-backed operational signals</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">Secondary intelligence</h2>
          <p className="mt-1 text-sm text-slate-600">Broker behavior, invoice risk, and assistant summaries stay below the primary work queue.</p>
        </div>
        <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Rules only</span>
      </div>

      {!assistant ? (
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <SkeletonBlock className="h-28" />
          <SkeletonBlock className="h-28" />
          <SkeletonBlock className="h-28" />
        </div>
      ) : (
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-950">Assistant summaries</h3>
            {insights.slice(0, 3).map((item) => (
              <div key={item.id} className={`rounded-2xl border p-4 text-sm ${severityClasses(item.severity)}`}>
                <div className="font-bold">{item.title}</div>
                <div className="mt-1 text-xs leading-5">{item.recommendation}</div>
              </div>
            ))}
            {insights.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">No elevated assistant summaries.</div> : null}
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-950">Invoice risk</h3>
            {invoiceRisks.slice(0, 3).map((item) => (
              <div key={`${item.load_id}:${item.risk_level}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
                <div className="font-bold text-slate-950">{item.broker_name ?? "Unknown broker"}</div>
                <div className="mt-1 text-xs text-slate-600">{item.outstanding_amount} outstanding · {item.age_days} days</div>
              </div>
            ))}
            {invoiceRisks.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">No elevated invoice risk.</div> : null}
          </div>
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-950">Broker behavior</h3>
            {brokerInsights.slice(0, 3).map((item) => (
              <div key={item.broker_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
                <div className="font-bold text-slate-950">{item.broker_name}</div>
                <div className="mt-1 text-xs text-slate-600">{item.unpaid_invoice_count} unpaid · trend {item.trend}</div>
              </div>
            ))}
            {brokerInsights.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">No elevated broker behavior signals.</div> : null}
          </div>
        </div>
      )}

      {recommendations.length > 0 ? (
        <div className="mt-5 flex flex-wrap gap-2">
          {recommendations.slice(0, 4).map((item) => {
            const href = isDashboardHref(item.href) ? item.href : "/dashboard";

            return <Link key={item.id} href={href} className="rounded-full bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700">{item.title}</Link>;
          })}
        </div>
      ) : null}
    </section>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [commandCenter, setCommandCenter] = useState<CommandCenterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [workMode, setWorkMode] = useState<WorkMode>("dispatcher");
  const { loads, isLoading: loadsLoading } = useLoads();

  useEffect(() => {
    const stored = window.localStorage.getItem(WORK_MODE_STORAGE_KEY);
    if (stored === "dispatcher" || stored === "billing" || stored === "collections") setWorkMode(stored);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(WORK_MODE_STORAGE_KEY, workMode);
  }, [workMode]);

  async function loadDashboard() {
    try {
      setLoading(true);
      setErrorMessage(null);
      const [data, commandCenterData] = await Promise.all([getDashboardMetrics(), getCommandCenter()]);
      setMetrics(data);
      setCommandCenter(commandCenterData);
    } catch (error: unknown) {
      const normalized = normalizeApiError(error, "Couldn’t refresh this panel. Retry or continue using workspace navigation.");
      setErrorMessage(normalized.requestId ? `${normalized.message} Reference: ${normalized.requestId}` : normalized.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const primaryKpis = [
    { label: "Missing Documents", value: metrics?.operational_queues?.missing_documents ?? commandCenter?.kpis.loads_missing_docs ?? 0, helper: "Loads blocked before packet completion", tone: "danger" as Tone, href: "/dashboard/loads?queue=missing_documents" },
    { label: "Ready to Invoice", value: metrics?.operational_queues?.ready_to_invoice ?? commandCenter?.kpis.loads_ready_for_invoice ?? metrics?.loads_ready_to_submit ?? 0, helper: "Packets ready for billing work", tone: "warning" as Tone, href: "/dashboard/billing" },
    { label: "Awaiting Submission", value: metrics?.operational_queues?.ready_to_submit ?? commandCenter?.kpis.loads_ready_to_submit ?? commandCenter?.kpis.pending_packet_sends ?? 0, helper: "Invoices or packets ready to send", tone: "warning" as Tone, href: "/dashboard/billing" },
    { label: "Payment Overdue", value: metrics?.operational_queues?.payment_overdue ?? commandCenter?.kpis.overdue_invoices ?? 0, helper: "Collection follow-up required", tone: "danger" as Tone, href: "/dashboard/money" },
    { label: "Open Follow-Ups", value: commandCenter?.tasks.summary.total ?? metrics?.operational_queues?.disputed_or_short_paid ?? 0, helper: "Owner-assigned operational next steps", tone: "default" as Tone, href: "/dashboard/follow-ups" },
  ] satisfies KpiCardProps[];

  const isFreshWorkspace = !loading && (metrics?.loads_total ?? 0) === 0;

  return (
    <div className="safe-page px-4 py-6 text-slate-900 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <CommandHeader metrics={metrics} workMode={workMode} setWorkMode={setWorkMode} refreshing={loading && Boolean(metrics)} />

        {errorMessage ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span>Couldn’t refresh this panel. Existing workspace navigation is still available.</span>
              <button type="button" onClick={() => void loadDashboard()} className="touch-target rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white">Retry</button>
            </div>
          </div>
        ) : null}

        <section aria-labelledby="primary-kpis">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 id="primary-kpis" className="text-lg font-bold text-slate-950">Primary operational KPIs</h2>
            <span className="text-xs font-semibold text-slate-500">High signal first</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {loading && !metrics ? primaryKpis.map((item) => <SkeletonBlock key={item.label} className="h-32" />) : primaryKpis.map((item) => <KpiCard key={item.label} {...item} />)}
          </div>
        </section>

        {isFreshWorkspace ? (
          <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-5 shadow-soft sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand-700">Guided setup</p>
            <h2 className="mt-2 text-xl font-bold text-slate-950">Build your first operating workflow</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Fresh workspaces are ready for dispatch, documents, driver coordination, carrier profile setup, and billing. Start with the profile or one load, then add paperwork and collaborators as the workflow grows.</p>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {emptyStateActions.map((action) => (
                <Link key={action.title} href={action.href} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50">
                  <div className="font-bold text-slate-950">{action.title}</div>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{action.helper}</p>
                </Link>
              ))}
            </div>
          </section>
        ) : null}

        <OperationalIntelligencePanel commandCenter={commandCenter} isLoading={loading} />

        <ActivePriorities loads={loads} workMode={workMode} isLoading={loadsLoading} />

        <SecondaryIntelligence commandCenter={commandCenter} />

        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-950">Quick access workspaces</h2>
            <p className="mt-1 text-sm text-slate-600">Jump into the core operational areas without scanning the full navigation tree.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {quickAccess.map((item) => (
              <Link key={item.title} href={item.href} className="touch-target rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50">
                <div className="text-sm font-bold text-slate-950">{item.title}</div>
                <div className="mt-1 text-xs text-slate-600">{item.helper}</div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
