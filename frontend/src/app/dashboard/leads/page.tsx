"use client";

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type LeadStatus = "new" | "contacted" | "scheduled" | "converted" | "lost";

type DemoLead = {
  id: string;
  fullName: string;
  email: string;
  company: string;
  phone: string | null;
  fleetSize: string | null;
  message: string | null;
  status: LeadStatus;
  notes: string | null;
  nextFollowUpAt: string | null;
  source: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};

type DraftState = {
  status: LeadStatus;
  notes: string;
  nextFollowUpAt: string;
};

type ApiEnvelope = {
  data?: unknown;
  meta?: Record<string, unknown>;
};

const STATUSES: LeadStatus[] = ["new", "contacted", "scheduled", "converted", "lost"];
const EMPTY_METRICS: Record<LeadStatus, number> = {
  new: 0,
  contacted: 0,
  scheduled: 0,
  converted: 0,
  lost: 0,
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeStatus(value: unknown): LeadStatus {
  const status = asString(value)?.toLowerCase();
  if (status === "closed") {
    return "lost";
  }
  return STATUSES.includes(status as LeadStatus) ? (status as LeadStatus) : "new";
}

function normalizeLead(value: unknown): DemoLead | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }
  const id = asString(record.id);
  const email = asString(record.email);
  if (!id || !email) {
    return null;
  }

  return {
    id,
    fullName: asString(record.full_name ?? record.fullName) ?? "Unknown contact",
    email,
    company: asString(record.company) ?? "Unknown company",
    phone: asString(record.phone),
    fleetSize: asString(record.fleet_size ?? record.fleetSize),
    message: asString(record.message),
    status: normalizeStatus(record.status),
    notes: asString(record.notes),
    nextFollowUpAt: asString(record.next_follow_up_at ?? record.nextFollowUpAt),
    source: asString(record.source),
    createdAt: asString(record.created_at ?? record.createdAt),
    updatedAt: asString(record.updated_at ?? record.updatedAt),
  };
}

function normalizeList(payload: unknown): { leads: DemoLead[]; metrics: Record<LeadStatus, number> } {
  const root = asRecord(payload);
  const rawItems = Array.isArray(root?.data) ? root.data : Array.isArray(payload) ? payload : [];
  const leads = rawItems.map(normalizeLead).filter((item): item is DemoLead => item !== null);
  const metricsRecord = asRecord(asRecord(root?.meta)?.metrics);
  const metrics = { ...EMPTY_METRICS };
  for (const status of STATUSES) {
    const value = metricsRecord?.[status];
    metrics[status] = typeof value === "number" ? value : Number(value ?? 0) || 0;
  }
  return { leads, metrics };
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function toDateTimeInput(value: string | null): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

function statusBadge(status: LeadStatus): string {
  switch (status) {
    case "new":
      return "bg-blue-100 text-blue-800";
    case "contacted":
      return "bg-amber-100 text-amber-800";
    case "scheduled":
      return "bg-indigo-100 text-indigo-800";
    case "converted":
      return "bg-emerald-100 text-emerald-800";
    case "lost":
      return "bg-slate-200 text-slate-700";
  }
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<DemoLead[]>([]);
  const [metrics, setMetrics] = useState<Record<LeadStatus, number>>(EMPTY_METRICS);
  const [statusFilter, setStatusFilter] = useState<"all" | LeadStatus>("all");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (search.trim()) {
      params.set("search", search.trim());
    }
    return params.toString();
  }, [statusFilter, search]);

  async function loadLeads() {
    setIsLoading(true);
    setError(null);
    try {
      const organizationId = getOrganizationId();
      if (!organizationId) {
        throw new Error("Missing organization context.");
      }
      const payload = await apiClient.get<ApiEnvelope>(`/demo-requests?${query}`, {
        token: getAccessToken() ?? undefined,
        organizationId,
      });
      const normalized = normalizeList(payload);
      setLeads(normalized.leads);
      setMetrics(normalized.metrics);
      setDrafts((current) => {
        const next = { ...current };
        for (const lead of normalized.leads) {
          next[lead.id] = next[lead.id] ?? {
            status: lead.status,
            notes: lead.notes ?? "",
            nextFollowUpAt: toDateTimeInput(lead.nextFollowUpAt),
          };
        }
        return next;
      });
    } catch {
      setError("Unable to load demo request leads. Please refresh and try again.");
      setLeads([]);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  function updateDraft(id: string, patch: Partial<DraftState>) {
    setDrafts((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
  }

  async function saveLead(lead: DemoLead) {
    const draft = drafts[lead.id];
    if (!draft) {
      return;
    }
    setSavingId(lead.id);
    setError(null);
    try {
      const organizationId = getOrganizationId();
      if (!organizationId) {
        throw new Error("Missing organization context.");
      }
      const body = {
        status: draft.status,
        notes: draft.notes,
        next_follow_up_at: draft.nextFollowUpAt ? new Date(draft.nextFollowUpAt).toISOString() : null,
      };
      const payload = await apiClient.patch<ApiEnvelope>(`/demo-requests/${lead.id}`, body, {
        token: getAccessToken() ?? undefined,
        organizationId,
      });
      const updated = normalizeLead(payload.data);
      if (updated) {
        setLeads((current) => current.map((item) => (item.id === updated.id ? updated : item)));
        setDrafts((current) => ({
          ...current,
          [updated.id]: {
            status: updated.status,
            notes: updated.notes ?? "",
            nextFollowUpAt: toDateTimeInput(updated.nextFollowUpAt),
          },
        }));
      }
      void loadLeads();
    } catch {
      setError("Unable to save lead updates. Please check the fields and try again.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Lead pipeline</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-950">Demo Requests</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Manage inbound request-demo leads from submission through outreach, scheduled demos, conversion, or loss.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadLeads()}
            className="touch-target rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Refresh
          </button>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(status)}
            className={`rounded-2xl border p-4 text-left shadow-soft transition ${
              statusFilter === status ? "border-brand-300 bg-brand-50" : "border-slate-200 bg-white hover:bg-slate-50"
            }`}
          >
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{labelize(status)}</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">{metrics[status]}</div>
          </button>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="grid gap-3 md:grid-cols-[1fr_220px_auto] md:items-end">
          <label className="block text-sm font-semibold text-slate-700">
            Search leads
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Name, company, email, or phone"
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block text-sm font-semibold text-slate-700">
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as "all" | LeadStatus)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="all">All statuses</option>
              {STATUSES.map((status) => (
                <option key={status} value={status}>{labelize(status)}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setStatusFilter("all");
            }}
            className="touch-target rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            Clear filters
          </button>
        </div>
      </section>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-700">{error}</div>
      ) : null}

      <section className="space-y-3">
        {isLoading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-soft">Loading demo request leads…</div>
        ) : leads.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-soft">No demo request leads match these filters.</div>
        ) : (
          leads.map((lead) => {
            const draft = drafts[lead.id] ?? {
              status: lead.status,
              notes: lead.notes ?? "",
              nextFollowUpAt: toDateTimeInput(lead.nextFollowUpAt),
            };
            const expanded = expandedId === lead.id;
            return (
              <article key={lead.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate text-lg font-bold text-slate-950">{lead.company}</h2>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadge(lead.status)}`}>{labelize(lead.status)}</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-600">{lead.fullName} · {lead.email}</div>
                    <div className="mt-2 grid gap-2 text-xs text-slate-500 sm:grid-cols-2 lg:grid-cols-4">
                      <div>Phone: <span className="font-medium text-slate-700">{lead.phone ?? "—"}</span></div>
                      <div>Fleet: <span className="font-medium text-slate-700">{lead.fleetSize ?? "—"}</span></div>
                      <div>Submitted: <span className="font-medium text-slate-700">{formatDateTime(lead.createdAt)}</span></div>
                      <div>Updated: <span className="font-medium text-slate-700">{formatDateTime(lead.updatedAt)}</span></div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : lead.id)}
                    className="touch-target rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    {expanded ? "Hide details" : "Manage lead"}
                  </button>
                </div>

                {expanded ? (
                  <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-[280px_1fr]">
                    <div className="space-y-3 text-sm text-slate-600">
                      <div><span className="font-semibold text-slate-800">Source:</span> {lead.source ?? "request_demo"}</div>
                      <div><span className="font-semibold text-slate-800">Follow-up:</span> {formatDateTime(lead.nextFollowUpAt)}</div>
                      <div>
                        <div className="font-semibold text-slate-800">Original message</div>
                        <p className="mt-1 whitespace-pre-wrap rounded-xl bg-slate-50 p-3">{lead.message ?? "No message provided."}</p>
                      </div>
                    </div>
                    <div className="grid gap-3">
                      <label className="block text-sm font-semibold text-slate-700">
                        Status
                        <select
                          value={draft.status}
                          onChange={(event) => updateDraft(lead.id, { status: event.target.value as LeadStatus })}
                          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        >
                          {STATUSES.map((status) => (
                            <option key={status} value={status}>{labelize(status)}</option>
                          ))}
                        </select>
                      </label>
                      <label className="block text-sm font-semibold text-slate-700">
                        Next follow-up
                        <input
                          type="datetime-local"
                          value={draft.nextFollowUpAt}
                          onChange={(event) => updateDraft(lead.id, { nextFollowUpAt: event.target.value })}
                          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                      </label>
                      <label className="block text-sm font-semibold text-slate-700">
                        Notes
                        <textarea
                          value={draft.notes}
                          onChange={(event) => updateDraft(lead.id, { notes: event.target.value.slice(0, 5000) })}
                          rows={5}
                          placeholder="Add outreach notes, scheduling context, blockers, or next steps."
                          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                      </label>
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <p className="text-xs text-slate-500">Notes are plain text and limited to 5,000 characters.</p>
                        <button
                          type="button"
                          onClick={() => void saveLead(lead)}
                          disabled={savingId === lead.id}
                          className="touch-target rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                        >
                          {savingId === lead.id ? "Saving…" : "Save lead"}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </section>
    </div>
  );
}
