"use client";

import Link from "next/link";

import { useLoads } from "@/hooks/useLoads";

function statusBadge(status?: string) {
  switch ((status ?? "").toLowerCase()) {
    case "needs_review":
      return "bg-amber-100 text-amber-800";
    case "validated":
      return "bg-emerald-100 text-emerald-800";
    case "submitted":
      return "bg-blue-100 text-blue-800";
    case "paid":
      return "bg-purple-100 text-purple-800";
    case "docs_received":
      return "bg-cyan-100 text-cyan-800";
    case "extracting":
      return "bg-indigo-100 text-indigo-800";
    case "ready_to_submit":
      return "bg-sky-100 text-sky-800";
    case "funded":
      return "bg-violet-100 text-violet-800";
    case "exception":
      return "bg-rose-100 text-rose-800";
    case "archived":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function statusLabel(status?: string) {
  const normalized = status?.trim();
  return normalized && normalized.length > 0
    ? normalized.replaceAll("_", " ")
    : "unknown";
}

function formatCurrency(value?: number | string | null) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const numericValue =
    typeof value === "string" ? Number.parseFloat(value) : value;

  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(numericValue);
}

export default function LoadsPage() {
  const { loads, isLoading, error } = useLoads();

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Loads
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Loads
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review active freight loads, document completeness, and current
              workflow state.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Filtering is not yet wired in V1."
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 opacity-60"
            >
              Filter
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Load creation is not yet wired in V1."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              New Load
            </button>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Load</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-5 py-8 text-center text-sm text-slate-500"
                    >
                      Loading loads...
                    </td>
                  </tr>
                ) : loads.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-5 py-8 text-center text-sm text-slate-500"
                    >
                      No loads found.
                    </td>
                  </tr>
                ) : (
                  loads.map((load) => (
                    <tr key={load.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900">
                          {load.load_number?.trim() || load.id}
                        </div>
                        <div className="text-xs text-slate-500">{load.id}</div>
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                            load.status
                          )}`}
                        >
                          {statusLabel(load.status)}
                        </span>
                      </td>

                      <td className="px-5 py-4 font-medium text-slate-900">
                        {formatCurrency(load.gross_amount)}
                      </td>

                      <td className="px-5 py-4">
                        <Link
                          href={`/dashboard/loads/${load.id}`}
                          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}