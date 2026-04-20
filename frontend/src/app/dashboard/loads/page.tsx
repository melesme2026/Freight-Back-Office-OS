"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

import { useLoads } from "@/hooks/useLoads";

type NullableString = string | null | undefined;
type NullableNumberLike = number | string | null | undefined;

type LoadListItem = {
  id: string;
  load_number?: NullableString;
  status?: NullableString;
  source_channel?: NullableString;
  processing_status?: NullableString;
  gross_amount?: NullableNumberLike;
  currency_code?: NullableString;
  broker_id?: NullableString;
  broker_name?: NullableString;
  broker_name_raw?: NullableString;
  broker_email_raw?: NullableString;
  customer_account_id?: NullableString;
  customer_account_name?: NullableString;
  driver_id?: NullableString;
  driver_name?: NullableString;
  pickup_location?: NullableString;
  delivery_location?: NullableString;
  pickup_date?: NullableString;
  delivery_date?: NullableString;
  has_ratecon?: boolean | null | undefined;
  has_bol?: boolean | null | undefined;
  has_invoice?: boolean | null | undefined;
  documents_complete?: boolean | null | undefined;
  operational?: {
    queue?: string;
    next_action?: { label?: string };
    is_overdue?: boolean;
    priority_score?: number;
  } | null;
};

type StatusFilter =
  | "all"
  | "invoice_ready"
  | "submitted_to_broker"
  | "submitted_to_factoring"
  | "packet_rejected"
  | "resubmission_needed"
  | "reserve_pending"
  | "advance_paid"
  | "short_paid"
  | "disputed"
  | "fully_paid";

function normalizeText(value: NullableString): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

function statusBadge(status?: string | null) {
  switch ((status ?? "").toLowerCase()) {
    case "docs_needs_attention":
      return "bg-amber-100 text-amber-800";
    case "submitted_to_broker":
      return "bg-blue-100 text-blue-800";
    case "fully_paid":
      return "bg-purple-100 text-purple-800";
    case "submitted_to_factoring":
      return "bg-indigo-100 text-indigo-800";
    case "invoice_ready":
      return "bg-emerald-100 text-emerald-800";
    case "reserve_pending":
      return "bg-violet-100 text-violet-800";
    case "advance_paid":
      return "bg-violet-100 text-violet-800";
    case "packet_rejected":
    case "resubmission_needed":
      return "bg-rose-100 text-rose-800";
    case "short_paid":
    case "disputed":
      return "bg-orange-100 text-orange-800";
    case "archived":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function statusLabel(status?: string | null) {
  const normalized = status?.trim();
  return normalized && normalized.length > 0
    ? normalized.replaceAll("_", " ")
    : "unknown";
}

function formatCurrency(
  value?: number | string | null,
  currencyCode?: string | null
) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const numericValue =
    typeof value === "string" ? Number.parseFloat(value) : value;

  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode?.trim() || "USD",
    }).format(numericValue);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(numericValue);
  }
}

function docCount(load: LoadListItem): number {
  return [
    load.has_ratecon === true,
    load.has_bol === true,
    load.has_invoice === true,
  ].filter(Boolean).length;
}

function docBadgeClass(load: LoadListItem): string {
  const count = docCount(load);

  if (count === 3) {
    return "bg-emerald-100 text-emerald-800";
  }

  if (count >= 1) {
    return "bg-amber-100 text-amber-800";
  }

  return "bg-rose-100 text-rose-800";
}

function docLabel(load: LoadListItem): string {
  return `${docCount(load)}/3 docs`;
}

function routeLabel(load: LoadListItem): string {
  const pickup = load.pickup_location?.trim() || "—";
  const delivery = load.delivery_location?.trim() || "—";
  return `${pickup} → ${delivery}`;
}

function getBrokerDisplay(load: LoadListItem): string {
  return (
    load.broker_name_raw?.trim() ||
    load.broker_name?.trim() ||
    load.broker_id?.trim() ||
    "—"
  );
}

function getDriverDisplay(load: LoadListItem): string {
  return load.driver_name?.trim() || load.driver_id?.trim() || "—";
}

function getCustomerDisplay(load: LoadListItem): string {
  return (
    load.customer_account_name?.trim() ||
    load.customer_account_id?.trim() ||
    "—"
  );
}

function matchesSearch(load: LoadListItem, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return true;
  }

  const haystacks: Array<NullableString> = [
    load.load_number,
    load.id,
    load.status,
    load.broker_name_raw,
    load.broker_name,
    load.broker_email_raw,
    load.customer_account_id,
    load.customer_account_name,
    load.driver_id,
    load.driver_name,
    load.pickup_location,
    load.delivery_location,
  ];

  return haystacks.some((value) => normalizeText(value).includes(normalizedQuery));
}

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "invoice_ready", label: "Ready to Submit" },
  { value: "submitted_to_broker", label: "Submitted to Broker" },
  { value: "submitted_to_factoring", label: "Submitted to Factoring" },
  { value: "packet_rejected", label: "Packet Rejected" },
  { value: "resubmission_needed", label: "Resubmission Needed" },
  { value: "advance_paid", label: "Advance Paid" },
  { value: "reserve_pending", label: "Reserve Pending" },
  { value: "short_paid", label: "Short Paid" },
  { value: "disputed", label: "Disputed" },
  { value: "fully_paid", label: "Fully Paid" },
];

export default function LoadsPage() {
  const { loads, isLoading, error } = useLoads();
  const searchParams = useSearchParams();
  const queueFilter = searchParams.get("queue")?.trim().toLowerCase() ?? "";

  async function handleExportCsv(): Promise<void> {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      return;
    }

    const blob = await apiClient.getBlob(`/loads/export.csv?organization_id=${encodeURIComponent(organizationId)}`, {
      token,
      organizationId,
    });

    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "loads-export.csv";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }
  const typedLoads = (loads ?? []) as LoadListItem[];

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const filteredLoads = useMemo(() => {
    return typedLoads
      .filter((load) => {
      const matchesStatus =
        statusFilter === "all"
          ? true
          : normalizeText(load.status) === statusFilter;

      const matchesQueue = queueFilter
        ? normalizeText(load.operational?.queue) === queueFilter
        : true;

      return matchesStatus && matchesQueue && matchesSearch(load, search);
    })
      .sort(
        (a, b) =>
          (b.operational?.priority_score ?? 0) - (a.operational?.priority_score ?? 0)
      );
  }, [typedLoads, search, statusFilter, queueFilter]);

  const metrics = useMemo(() => {
    const total = typedLoads.length;
    const active = typedLoads.filter(
      (load) => normalizeText(load.status) !== "archived"
    ).length;
    const waiting = typedLoads.filter((load) =>
      ["submitted_to_broker", "reserve_pending"].includes(normalizeText(load.status))
    ).length;
    const submittedToBroker = typedLoads.filter(
      (load) => normalizeText(load.status) === "submitted_to_broker"
    ).length;
    const followUp = typedLoads.filter(
      (load) => normalizeText(load.status) === "invoice_ready"
    ).length;
    const paid = typedLoads.filter((load) => normalizeText(load.status) === "fully_paid").length;
    const missingDocs = typedLoads.filter((load) => docCount(load) < 3).length;

    return { total, active, waiting, submittedToBroker, followUp, paid, missingDocs };
  }, [typedLoads]);

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
            {queueFilter ? (
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
                Queue: {queueFilter.replaceAll("_", " ")}
              </p>
            ) : null}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => void handleExportCsv()}
              className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2"
            >
              Export CSV
            </button>
            <Link
              href="/dashboard/loads/new"
              className="inline-flex items-center rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              New Load
            </Link>
          </div>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Total Loads
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-950">
              {metrics.total}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Active
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-950">
              {metrics.active}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Submitted to Broker
            </div>
            <div className="mt-2 text-2xl font-bold text-amber-700">
              {metrics.submittedToBroker}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Waiting
            </div>
            <div className="mt-2 text-2xl font-bold text-amber-700">
              {metrics.waiting}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Ready to Submit
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-700">
              {metrics.followUp}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Paid
            </div>
            <div className="mt-2 text-2xl font-bold text-purple-700">
              {metrics.paid}
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="grid gap-4 md:grid-cols-[1fr,220px]">
            <div>
              <label
                htmlFor="loadSearch"
                className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                Search
              </label>
              <input
                id="loadSearch"
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by load, broker, route, customer, driver, or ID"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label
                htmlFor="statusFilter"
                className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                Status
              </label>
              <select
                id="statusFilter"
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(event.target.value as StatusFilter)
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
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
                  <th className="px-5 py-4 font-semibold">Route / Parties</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Docs</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                  <th className="px-5 py-4 font-semibold">Next Action</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-8 text-center text-sm text-slate-500"
                    >
                      Loading loads...
                    </td>
                  </tr>
                ) : filteredLoads.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-8 text-center text-sm text-slate-500"
                    >
                      {typedLoads.length === 0
                        ? "No loads found. Create one with New Load or seed demo records using `make seed-dev-data`."
                        : "No loads match the current search or filter."}
                    </td>
                  </tr>
                ) : (
                  filteredLoads.map((load) => (
                    <tr key={load.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4 align-top">
                        <div className="font-semibold text-slate-900">
                          {load.load_number?.trim() || load.id}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {load.id}
                        </div>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <div className="space-y-1">
                          <div className="text-sm font-medium text-slate-900">
                            {routeLabel(load)}
                          </div>
                          <div className="text-xs text-slate-500">
                            Broker: {getBrokerDisplay(load)}
                          </div>
                          <div className="text-xs text-slate-500">
                            Driver: {getDriverDisplay(load)}
                          </div>
                          <div className="text-xs text-slate-500">
                            Customer: {getCustomerDisplay(load)}
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                            load.status
                          )}`}
                        >
                          {statusLabel(load.status)}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${docBadgeClass(
                            load
                          )}`}
                        >
                          {docLabel(load)}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top font-medium text-slate-900">
                        {formatCurrency(load.gross_amount, load.currency_code)}
                      </td>

                      <td className="px-5 py-4 align-top">
                        <div className="text-sm text-slate-700">
                          {load.operational?.next_action?.label || "Monitor load"}
                        </div>
                        {load.operational?.is_overdue ? (
                          <span className="mt-1 inline-flex rounded-full bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                            Overdue follow-up
                          </span>
                        ) : null}
                      </td>

                      <td className="px-5 py-4 align-top">
                        <Link
                          href={`/dashboard/loads/${load.id}`}
                          className="text-sm font-semibold text-brand-700 transition hover:text-brand-800"
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

        {!isLoading && typedLoads.length > 0 ? (
          <div className="mt-4 text-sm text-slate-500">
            Showing {filteredLoads.length} of {typedLoads.length} loads.
          </div>
        ) : null}
      </div>
    </main>
  );
}
