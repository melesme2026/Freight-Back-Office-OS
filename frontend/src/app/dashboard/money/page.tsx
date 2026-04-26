"use client";

import { useEffect, useState } from "react";

import { getUserRole } from "@/lib/auth";
import { getMoneyDashboard, type MoneyDashboardResponse } from "@/lib/money-dashboard";
import { isDriverRole } from "@/lib/rbac";

function formatCurrency(value: string | number | null | undefined): string {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount)
    ? amount.toLocaleString("en-US", { style: "currency", currency: "USD" })
    : "$0.00";
}

export default function MoneyDashboardPage() {
  const [data, setData] = useState<MoneyDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        setData(await getMoneyDashboard());
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load money dashboard.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  if (isDriverRole(getUserRole())) {
    return <div className="p-6 text-sm text-rose-700">Drivers cannot access the Money Dashboard.</div>;
  }

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header>
          <p className="text-sm font-medium text-brand-700">Cash Visibility</p>
          <h1 className="text-3xl font-bold text-slate-950">Money Dashboard</h1>
        </header>

        {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-5">Loading money dashboard...</div> : null}
        {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-700">{error}</div> : null}

        {!loading && !error && data ? (
          <>
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[
                ["Total Receivables", data.summary.total_receivables],
                ["Outstanding", data.summary.total_outstanding],
                ["Received", data.summary.total_received],
                ["Overdue", data.summary.overdue_amount],
                ["Reserve Pending", data.summary.reserve_pending_amount],
                ["Disputed / Short-Pay", `${data.summary.disputed_count ?? 0} / ${data.summary.short_paid_count ?? 0}`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                  <div className="text-sm text-slate-500">{label}</div>
                  <div className="mt-2 text-2xl font-semibold text-slate-950">
                    {typeof value === "string" && value.includes("/") ? value : formatCurrency(value as string | number)}
                  </div>
                </div>
              ))}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Aging Buckets</h2>
              {data.aging_buckets.length === 0 ? <p className="mt-3 text-sm text-slate-500">No aging data available.</p> : (
                <table className="mt-3 min-w-full text-sm">
                  <thead><tr className="text-left text-slate-500"><th>Bucket</th><th>Count</th><th>Amount</th></tr></thead>
                  <tbody>{data.aging_buckets.map((row) => <tr key={row.bucket} className="border-t border-slate-100"><td className="py-2">{row.bucket}</td><td>{row.count}</td><td>{formatCurrency(row.amount)}</td></tr>)}</tbody>
                </table>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Payment Status Breakdown</h2>
              <table className="mt-3 min-w-full text-sm">
                <thead><tr className="text-left text-slate-500"><th>Status</th><th>Count</th><th>Amount</th></tr></thead>
                <tbody>{data.status_breakdown.map((row) => <tr key={row.status} className="border-t border-slate-100"><td className="py-2">{row.status.replaceAll("_", " ")}</td><td>{row.count}</td><td>{formatCurrency(row.amount)}</td></tr>)}</tbody>
              </table>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-semibold">Factoring vs Direct</h2>
                <div className="mt-3 space-y-1 text-sm text-slate-700">
                  <div>Factored loads: {data.factoring_vs_direct.factored.count} ({formatCurrency(data.factoring_vs_direct.factored.amount)})</div>
                  <div>Direct loads: {data.factoring_vs_direct.direct.count} ({formatCurrency(data.factoring_vs_direct.direct.amount)})</div>
                  <div>Advances paid: {formatCurrency(data.factoring_vs_direct.advance_total)}</div>
                  <div>Reserve pending: {formatCurrency(data.factoring_vs_direct.reserve_pending_total)}</div>
                  <div>Direct unpaid: {formatCurrency(data.factoring_vs_direct.direct_unpaid_total)}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-semibold">Needs Attention Today</h2>
                <div className="mt-3 text-sm text-slate-700">Urgent follow-ups: {data.needs_attention.urgent_count}</div>
                <div className="text-sm text-slate-700">Overdue follow-ups: {data.needs_attention.overdue_followups_count}</div>
                {data.needs_attention.top_items.length === 0 ? <p className="mt-3 text-sm text-slate-500">No follow-up items due today.</p> : (
                  <table className="mt-3 min-w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Load</th><th>Task</th><th>Priority</th><th>Due</th></tr></thead><tbody>{data.needs_attention.top_items.map((item) => <tr key={`${item.load_id}-${item.task_type}`} className="border-t border-slate-100"><td className="py-2">{item.load_number ?? item.load_id.slice(0, 8)}</td><td>{item.recommended_action ?? item.task_type.replaceAll("_", " ")}</td><td>{item.priority}</td><td>{new Date(item.due_at).toLocaleDateString()}</td></tr>)}</tbody></table>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Recent Cash Activity</h2>
              {data.recent_cash_activity.length === 0 ? <p className="mt-3 text-sm text-slate-500">No recent payment activity.</p> : (
                <table className="mt-3 min-w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Load Number</th><th>Amount Received</th><th>Paid Date</th><th>Status</th></tr></thead><tbody>{data.recent_cash_activity.map((item, idx) => <tr key={`${item.load_number}-${idx}`} className="border-t border-slate-100"><td className="py-2">{item.load_number ?? "—"}</td><td>{formatCurrency(item.amount_received)}</td><td>{new Date(item.paid_date).toLocaleDateString()}</td><td>{item.payment_status.replaceAll("_", " ")}</td></tr>)}</tbody></table>
              )}
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}
