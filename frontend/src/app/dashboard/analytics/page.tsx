"use client";

import { useEffect, useMemo, useState } from "react";

import { getUserRole } from "@/lib/auth";
import { getOperationalAnalytics, type AgingBucket, type InvoiceRiskItem, type OperationalAnalyticsResponse, type PerformanceRow, type RevenueTrend } from "@/lib/operational-analytics";
import { isDriverRole } from "@/lib/rbac";

function formatCurrency(value: string | number | null | undefined): string {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount)
    ? amount.toLocaleString("en-US", { style: "currency", currency: "USD" })
    : "$0.00";
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function toNumber(value: string | number | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function Card({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-bold text-slate-950">{value}</div>
      {helper ? <div className="mt-1 text-xs text-slate-500">{helper}</div> : null}
    </div>
  );
}

function BarChart({ rows, valueKey, labelKey, emptyLabel }: { rows: Array<Record<string, unknown>>; valueKey: string; labelKey: string; emptyLabel: string }) {
  const max = Math.max(1, ...rows.map((row) => toNumber(row[valueKey] as string | number)));
  if (rows.length === 0) {
    return <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">{emptyLabel}</div>;
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => {
        const value = toNumber(row[valueKey] as string | number);
        const width = Math.max(4, Math.round((value / max) * 100));
        return (
          <div key={String(row[labelKey])}>
            <div className="flex items-center justify-between gap-3 text-xs text-slate-600">
              <span className="truncate font-medium text-slate-700">{String(row[labelKey])}</span>
              <span>{formatCurrency(value)}</span>
            </div>
            <div className="mt-1 h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-brand-600" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AgingDistribution({ buckets }: { buckets: AgingBucket[] }) {
  return <BarChart rows={buckets as unknown as Array<Record<string, unknown>>} valueKey="balance" labelKey="label" emptyLabel="No unpaid balances in aging buckets." />;
}

function RevenueTrendChart({ trends }: { trends: RevenueTrend[] }) {
  return <BarChart rows={trends as unknown as Array<Record<string, unknown>>} valueKey="revenue" labelKey="month" emptyLabel="No revenue trend data for this range." />;
}

function PerformanceTable({ rows, kind }: { rows: PerformanceRow[]; kind: "driver" | "broker" | "lane" }) {
  return (
    <div className="mobile-scroll-area overflow-x-auto">
      <table className="min-w-[760px] divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">{kind === "lane" ? "Lane" : kind === "broker" ? "Broker" : "Driver"}</th>
            <th className="px-3 py-3">Loads</th>
            <th className="px-3 py-3">Revenue</th>
            <th className="px-3 py-3">Avg load</th>
            <th className="px-3 py-3">Unpaid</th>
            <th className="px-3 py-3">Overdue</th>
            <th className="px-3 py-3">Factored</th>
            {kind === "broker" ? <th className="px-3 py-3">Avg pay days</th> : null}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.length === 0 ? (
            <tr><td colSpan={kind === "broker" ? 8 : 7} className="px-3 py-4 text-slate-500">No rows for the current filters.</td></tr>
          ) : rows.map((row) => (
            <tr key={`${kind}-${row.id}`}>
              <td className="max-w-[260px] px-3 py-3 font-medium text-slate-900">{row.name}</td>
              <td className="px-3 py-3 text-slate-600">{row.load_count}</td>
              <td className="px-3 py-3 text-slate-600">{formatCurrency(row.revenue)}</td>
              <td className="px-3 py-3 text-slate-600">{formatCurrency(row.average_load_value)}</td>
              <td className="px-3 py-3 text-slate-600">{formatCurrency(row.unpaid_balance)}</td>
              <td className="px-3 py-3 text-slate-600">{row.overdue_count} / {formatCurrency(row.overdue_balance)}</td>
              <td className="px-3 py-3 text-slate-600">{formatCurrency(row.factored_revenue)}</td>
              {kind === "broker" ? <td className="px-3 py-3 text-slate-600">{row.average_payment_days ?? "—"}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InvoiceTable({ rows }: { rows: InvoiceRiskItem[] }) {
  return (
    <div className="mobile-scroll-area overflow-x-auto">
      <table className="min-w-[920px] divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-3 py-3">Load / Invoice</th>
            <th className="px-3 py-3">Broker</th>
            <th className="px-3 py-3">Driver</th>
            <th className="px-3 py-3">Lane</th>
            <th className="px-3 py-3">Status</th>
            <th className="px-3 py-3">Outstanding</th>
            <th className="px-3 py-3">Age</th>
            <th className="px-3 py-3">Recon</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.length === 0 ? (
            <tr><td colSpan={8} className="px-3 py-4 text-slate-500">No unpaid invoices for the current filters.</td></tr>
          ) : rows.map((row) => (
            <tr key={`${row.load_id}-${row.payment_status}`}>
              <td className="px-3 py-3 font-medium text-slate-900">{row.load_number ?? "—"}<div className="text-xs font-normal text-slate-500">{row.invoice_number ?? "No invoice #"}</div></td>
              <td className="px-3 py-3 text-slate-600">{row.broker_name ?? "—"}</td>
              <td className="px-3 py-3 text-slate-600">{row.driver_name ?? "—"}</td>
              <td className="max-w-[260px] px-3 py-3 text-slate-600">{row.lane}</td>
              <td className="px-3 py-3 text-slate-600">{formatLabel(row.payment_status)}</td>
              <td className="px-3 py-3 text-slate-600">{formatCurrency(row.outstanding_amount)}</td>
              <td className="px-3 py-3 text-slate-600">{row.age_days} days</td>
              <td className="px-3 py-3 text-slate-600">{formatLabel(row.reconciliation_status)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function exportCsv(data: OperationalAnalyticsResponse) {
  const rows = [
    ["section", "name", "loads", "revenue", "unpaid", "overdue", "factored"],
    ...data.driver_profitability.map((row) => ["driver", row.name, row.load_count, row.revenue, row.unpaid_balance, row.overdue_balance, row.factored_revenue]),
    ...data.broker_performance.map((row) => ["broker", row.name, row.load_count, row.revenue, row.unpaid_balance, row.overdue_balance, row.factored_revenue]),
    ...data.lane_profitability.map((row) => ["lane", row.name, row.load_count, row.revenue, row.unpaid_balance, row.overdue_balance, row.factored_revenue]),
  ];
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "operational-analytics.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function AnalyticsDashboardPage() {
  const [data, setData] = useState<OperationalAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [brokerId, setBrokerId] = useState("");
  const [driverId, setDriverId] = useState("");
  const [factoringStatus, setFactoringStatus] = useState("");

  async function loadAnalytics() {
    try {
      setLoading(true);
      setError(null);
      setData(await getOperationalAnalytics({ dateFrom, dateTo, brokerId, driverId, factoringStatus }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const brokerRankingRows = useMemo(() => (data?.broker_performance ?? []).slice(0, 6) as unknown as Array<Record<string, unknown>>, [data]);

  if (isDriverRole(getUserRole())) {
    return <div className="p-6 text-sm text-rose-700">Drivers cannot access operational analytics.</div>;
  }

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Operational BI</p>
            <h1 className="text-3xl font-bold text-slate-950">Analytics & Reporting</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">Revenue, collections, aging, broker, driver, and lane visibility built from explainable load payment data.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => void loadAnalytics()} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700">Refresh</button>
            <button type="button" onClick={() => data ? exportCsv(data) : undefined} disabled={!data} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300">Export CSV</button>
          </div>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <label className="text-xs font-semibold uppercase text-slate-500">Date from<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm normal-case text-slate-900" /></label>
            <label className="text-xs font-semibold uppercase text-slate-500">Date to<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm normal-case text-slate-900" /></label>
            <label className="text-xs font-semibold uppercase text-slate-500">Broker<select value={brokerId} onChange={(event) => setBrokerId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm normal-case text-slate-900"><option value="">All brokers</option>{data?.filter_options.brokers.map((broker) => <option key={broker.id} value={broker.id}>{broker.name}</option>)}</select></label>
            <label className="text-xs font-semibold uppercase text-slate-500">Driver<select value={driverId} onChange={(event) => setDriverId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm normal-case text-slate-900"><option value="">All drivers</option>{data?.filter_options.drivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}</select></label>
            <label className="text-xs font-semibold uppercase text-slate-500">Factoring<select value={factoringStatus} onChange={(event) => setFactoringStatus(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm normal-case text-slate-900"><option value="">All statuses</option>{data?.filter_options.factoring_statuses.map((status) => <option key={status} value={status}>{formatLabel(status)}</option>)}</select></label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={() => void loadAnalytics()} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white">Apply filters</button>
            <button type="button" onClick={() => { setDateFrom(""); setDateTo(""); setBrokerId(""); setDriverId(""); setFactoringStatus(""); }} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Clear fields</button>
          </div>
        </section>

        {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Loading analytics…</div> : null}
        {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">{error}</div> : null}

        {!loading && !error && data ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Card label="Total revenue" value={formatCurrency(data.revenue.total_revenue)} helper={`${data.revenue.invoice_count} invoices / loads`} />
              <Card label="Paid revenue" value={formatCurrency(data.revenue.paid_revenue)} helper={`${formatCurrency(data.revenue.received_revenue)} received total`} />
              <Card label="Unpaid revenue" value={formatCurrency(data.revenue.unpaid_revenue)} helper={`${data.unpaid_invoices.unpaid_count} unpaid records`} />
              <Card label="Factored revenue" value={formatCurrency(data.revenue.factored_revenue)} helper="Factoring-used or factored status" />
              <Card label="Average invoice" value={formatCurrency(data.revenue.average_invoice_amount)} />
              <Card label="Overdue balance" value={formatCurrency(data.collections.overdue_balance)} helper={`${data.unpaid_invoices.overdue_count} overdue`} />
              <Card label="Reserve pending" value={formatCurrency(data.collections.reserve_pending_total)} />
              <Card label="Unreconciled" value={String(data.collections.unreconciled_count)} helper={formatCurrency(data.collections.unreconciled_balance)} />
            </section>

            <section className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-bold text-slate-950">Monthly revenue trend</h2>
                <p className="mb-4 mt-1 text-sm text-slate-500">Expected revenue by selected operational reference date.</p>
                <RevenueTrendChart trends={data.revenue.monthly_trends} />
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-bold text-slate-950">Aging distribution</h2>
                <p className="mb-4 mt-1 text-sm text-slate-500">Unpaid balances split into current, 1–15, 16–30, 31–60, and 60+ day buckets.</p>
                <AgingDistribution buckets={data.aging_report.buckets} />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-bold text-slate-950">Unpaid invoices & collections risk</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <Card label="High risk" value={formatCurrency(data.collections.risk_summary.high_risk_balance)} helper={`${data.collections.risk_summary.high_risk_count} invoices`} />
                <Card label="Medium risk" value={formatCurrency(data.collections.risk_summary.medium_risk_balance)} helper={`${data.collections.risk_summary.medium_risk_count} invoices`} />
                <Card label="Low risk" value={formatCurrency(data.collections.risk_summary.low_risk_balance)} helper={`${data.collections.risk_summary.low_risk_count} invoices`} />
              </div>
              <div className="mt-5"><InvoiceTable rows={data.unpaid_invoices.items} /></div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-bold text-slate-950">Broker ranking</h2>
                <p className="mb-4 mt-1 text-sm text-slate-500">Revenue by broker with aging exposure shown in the table.</p>
                <BarChart rows={brokerRankingRows} valueKey="revenue" labelKey="name" emptyLabel="No broker revenue for this range." />
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-bold text-slate-950">Broker performance</h2>
                <PerformanceTable rows={data.broker_performance} kind="broker" />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-bold text-slate-950">Driver profitability (revenue-only)</h2>
              <p className="mb-4 mt-1 text-sm text-slate-500">No margin is inferred; profitability uses actual revenue, collections, and factoring visibility only.</p>
              <PerformanceTable rows={data.driver_profitability} kind="driver" />
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-bold text-slate-950">Lane profitability (revenue-only)</h2>
              <p className="mb-4 mt-1 text-sm text-slate-500">Pickup → delivery groupings with deterministic revenue and unpaid exposure.</p>
              <PerformanceTable rows={data.lane_profitability} kind="lane" />
            </section>

            <section className="rounded-2xl border border-slate-200 bg-slate-950 p-5 text-white shadow-soft">
              <h2 className="text-lg font-bold">Metric definitions</h2>
              <dl className="mt-3 grid gap-3 md:grid-cols-2">
                {Object.entries(data.metric_definitions).map(([key, value]) => (
                  <div key={key} className="rounded-xl bg-white/10 p-3">
                    <dt className="text-sm font-semibold">{formatLabel(key)}</dt>
                    <dd className="mt-1 text-xs leading-5 text-slate-200">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}
