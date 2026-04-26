"use client";

import { useEffect, useMemo, useState } from "react";

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
  const [statusFilter, setStatusFilter] = useState("all");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [channelFilter, setChannelFilter] = useState<"all" | "factoring" | "direct">("all");
  const [search, setSearch] = useState("");

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

  const filteredCashActivity = useMemo(() => {
    if (!data) return [];
    return data.recent_cash_activity.filter((item) => {
      if (statusFilter !== "all" && item.payment_status !== statusFilter) return false;
      if (channelFilter === "factoring" && !item.factoring_used) return false;
      if (channelFilter === "direct" && item.factoring_used) return false;
      if (overdueOnly && item.payment_status !== "overdue") return false;
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        const loadNumber = (item.load_number ?? "").toLowerCase();
        if (!loadNumber.includes(q) && !item.payment_status.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [channelFilter, data, overdueOnly, search, statusFilter]);

  if (isDriverRole(getUserRole())) {
    return <div className="p-6 text-sm text-rose-700">Drivers cannot access the Money Dashboard.</div>;
  }

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Cash Visibility</p>
            <h1 className="text-3xl font-bold text-slate-950">Money Dashboard</h1>
          </div>
          <button type="button" onClick={() => window.location.reload()} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700">Refresh</button>
        </header>

        {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Loading money dashboard data…</div> : null}
        {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-700">{error}</div> : null}

        {!loading && !error && data ? (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs font-semibold uppercase text-slate-500">Payment status
                  <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="mt-1 block rounded-lg border border-slate-300 px-2 py-2 text-sm">
                    <option value="all">All</option>
                    {data.status_breakdown.map((row) => <option key={row.status} value={row.status}>{row.status.replaceAll("_", " ")}</option>)}
                  </select>
                </label>
                <label className="text-xs font-semibold uppercase text-slate-500">Factoring/direct
                  <select value={channelFilter} onChange={(event) => setChannelFilter(event.target.value as "all" | "factoring" | "direct")} className="mt-1 block rounded-lg border border-slate-300 px-2 py-2 text-sm">
                    <option value="all">All</option>
                    <option value="factoring">Factoring</option>
                    <option value="direct">Direct</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 pt-5 text-sm text-slate-700"><input type="checkbox" checked={overdueOnly} onChange={(event) => setOverdueOnly(event.target.checked)} />Overdue only</label>
                <label className="min-w-52 flex-1 text-xs font-semibold uppercase text-slate-500">Search
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Load # or status" className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm" />
                </label>
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
                <h2 className="text-lg font-semibold">Payment Status Breakdown</h2>
                {data.status_breakdown.length === 0 ? <p className="mt-3 text-sm text-slate-500">No status data available.</p> : (
                  <div className="mt-3 overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Status</th><th>Count</th><th>Amount</th></tr></thead><tbody>{data.status_breakdown.map((row) => <tr key={row.status} className="border-t border-slate-100"><td className="py-2">{row.status.replaceAll("_", " ")}</td><td>{row.count}</td><td>{formatCurrency(row.amount)}</td></tr>)}</tbody></table></div>
                )}
              </div>
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
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Recent Cash Activity</h2>
              {filteredCashActivity.length === 0 ? <p className="mt-3 text-sm text-slate-500">No activity matches current filters.</p> : (
                <div className="mt-3 overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Load Number</th><th>Amount Received</th><th>Paid Date</th><th>Status</th><th>Channel</th></tr></thead><tbody>{filteredCashActivity.map((item, idx) => <tr key={`${item.load_number}-${idx}`} className="border-t border-slate-100"><td className="py-2">{item.load_number ?? "—"}</td><td>{formatCurrency(item.amount_received)}</td><td>{new Date(item.paid_date).toLocaleDateString()}</td><td>{item.payment_status.replaceAll("_", " ")}</td><td>{item.factoring_used ? "Factoring" : "Direct"}</td></tr>)}</tbody></table></div>
              )}
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}
