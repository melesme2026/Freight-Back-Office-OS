"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { useBrokers } from "@/hooks/useBrokers";

function formatTerms(value?: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }

  return `${Math.max(0, Math.floor(value))} days`;
}

export default function BrokersPage() {
  const router = useRouter();
  const { brokers, isLoading, error, refetch } = useBrokers();

  const totals = useMemo(() => ({
    total: brokers.length,
    withEmail: brokers.filter((broker) => Boolean(broker.email)).length,
    withMc: brokers.filter((broker) => Boolean(broker.mc_number)).length,
  }), [brokers]);

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Brokers</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Brokers</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Maintain broker contacts, MC identifiers, and payment terms used in load operations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isLoading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
            <button
              type="button"
              onClick={() => router.push("/dashboard/brokers/new")}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              Add Broker
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total brokers</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{isLoading ? "..." : totals.total}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">With email</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{isLoading ? "..." : totals.withEmail}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">With MC number</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{isLoading ? "..." : totals.withMc}</div>
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Broker</th>
                  <th className="px-5 py-4 font-semibold">MC</th>
                  <th className="px-5 py-4 font-semibold">Email</th>
                  <th className="px-5 py-4 font-semibold">Phone</th>
                  <th className="px-5 py-4 font-semibold">Payment Terms</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-500">Loading brokers...</td></tr>
                ) : brokers.length === 0 ? (
                  <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-500">No brokers found. Add one to improve load handoff workflows.</td></tr>
                ) : brokers.map((broker) => (
                  <tr key={broker.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{broker.name}</div>
                      <div className="text-xs text-slate-500">{broker.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{broker.mc_number || "—"}</td>
                    <td className="px-5 py-4 text-slate-700">{broker.email || "—"}</td>
                    <td className="px-5 py-4 text-slate-700">{broker.phone || "—"}</td>
                    <td className="px-5 py-4 text-slate-700">{formatTerms(broker.payment_terms_days)}</td>
                    <td className="px-5 py-4">
                      <button
                        type="button"
                        onClick={() => router.push(`/dashboard/brokers/${broker.id}`)}
                        className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                      >
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
