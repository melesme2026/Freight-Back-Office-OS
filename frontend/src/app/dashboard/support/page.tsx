"use client";

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type ApiError = {
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
};

type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
  error?: ApiError | null;
};

type SupportTicket = {
  id: string;
  organization_id: string;
  customer_account_id?: string | null;
  driver_id?: string | null;
  load_id?: string | null;
  assigned_to_staff_user_id?: string | null;
  subject: string;
  description: string;
  status: string;
  priority: string;
  resolved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function normalizeSupportTicket(value: unknown): SupportTicket | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const id = asString(record.id);
  const organizationId = asString(record.organization_id);
  const subject = asString(record.subject);
  const description = asString(record.description);
  const status = asString(record.status);
  const priority = asString(record.priority);

  if (!id || !organizationId || !subject || !description || !status || !priority) {
    return null;
  }

  return {
    id,
    organization_id: organizationId,
    customer_account_id: asString(record.customer_account_id),
    driver_id: asString(record.driver_id),
    load_id: asString(record.load_id),
    assigned_to_staff_user_id: asString(record.assigned_to_staff_user_id),
    subject,
    description,
    status,
    priority,
    resolved_at: asString(record.resolved_at),
    created_at: asString(record.created_at),
    updated_at: asString(record.updated_at),
  };
}

function normalizeSupportTicketsResponse(payload: unknown): SupportTicket[] {
  const root = asRecord(payload);

  if (!root) {
    return [];
  }

  const candidates = Array.isArray(root.data)
    ? root.data
    : Array.isArray(root.items)
      ? root.items
      : Array.isArray(payload)
        ? payload
        : [];

  return candidates
    .map((item) => normalizeSupportTicket(item))
    .filter((item): item is SupportTicket => item !== null);
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function statusBadgeClass(status?: string) {
  switch ((status ?? "").toLowerCase()) {
    case "open":
      return "bg-blue-100 text-blue-800";
    case "in_progress":
    case "in progress":
      return "bg-amber-100 text-amber-800";
    case "resolved":
      return "bg-emerald-100 text-emerald-800";
    case "closed":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function priorityBadgeClass(priority?: string) {
  switch ((priority ?? "").toLowerCase()) {
    case "urgent":
      return "bg-rose-100 text-rose-800";
    case "high":
      return "bg-orange-100 text-orange-800";
    case "normal":
      return "bg-sky-100 text-sky-800";
    case "low":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function truncateText(value: string, maxLength = 140): string {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 1)}…`;
}

export default function SupportPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadSupportTickets() {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      setTickets([]);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage(null);

      const payload = await apiClient.get<ApiResponse<unknown>>(
        "/support/tickets?page=1&page_size=50",
        {
          token,
          organizationId,
        }
      );

      setTickets(normalizeSupportTicketsResponse(payload));
    } catch (error) {
      setTickets([]);
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : "Failed to load support tickets."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadSupportTickets();
  }, []);

  const metrics = useMemo(() => {
    const total = tickets.length;
    const open = tickets.filter((ticket) => ticket.status.toLowerCase() === "open").length;
    const resolved = tickets.filter(
      (ticket) => ticket.status.toLowerCase() === "resolved"
    ).length;
    const urgentOrHigh = tickets.filter((ticket) =>
      ["urgent", "high"].includes(ticket.priority.toLowerCase())
    ).length;

    return {
      total,
      open,
      resolved,
      urgentOrHigh,
    };
  }, [tickets]);

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Support</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Monitor operational tickets, customer issues, and escalation readiness using
              live support data from the backend.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void loadSupportTickets()}
              disabled={isLoading}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-soft transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total tickets</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : metrics.total}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Open</div>
            <div className="mt-2 text-3xl font-bold text-blue-700">
              {isLoading ? "..." : metrics.open}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Resolved</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">
              {isLoading ? "..." : metrics.resolved}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Urgent / High</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">
              {isLoading ? "..." : metrics.urgentOrHigh}
            </div>
          </div>
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-rose-800">
                  Unable to load support tickets
                </h2>
                <p className="mt-1 text-sm text-rose-700">{errorMessage}</p>
              </div>

              <button
                type="button"
                onClick={() => void loadSupportTickets()}
                className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Subject</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Priority</th>
                  <th className="px-5 py-4 font-semibold">Linked Records</th>
                  <th className="px-5 py-4 font-semibold">Updated</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                      Loading support tickets...
                    </td>
                  </tr>
                ) : tickets.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                      No support tickets found.
                    </td>
                  </tr>
                ) : (
                  tickets.map((ticket) => (
                    <tr key={ticket.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4 align-top">
                        <div className="font-semibold text-slate-900">{ticket.subject}</div>
                        <div className="mt-1 text-xs text-slate-500">{ticket.id}</div>
                        <div className="mt-2 text-sm text-slate-600">
                          {truncateText(ticket.description)}
                        </div>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(
                            ticket.status
                          )}`}
                        >
                          {ticket.status.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${priorityBadgeClass(
                            ticket.priority
                          )}`}
                        >
                          {ticket.priority.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        <div>Customer: {ticket.customer_account_id ?? "—"}</div>
                        <div className="mt-1">Driver: {ticket.driver_id ?? "—"}</div>
                        <div className="mt-1">Load: {ticket.load_id ?? "—"}</div>
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {formatDateTime(ticket.updated_at ?? ticket.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            This page now reflects live backend support tickets. Creation, assignment,
            and richer ticket-detail workflows can be added next if the corresponding
            frontend routes are still missing.
          </p>
        </section>
      </div>
    </div>
  );
}