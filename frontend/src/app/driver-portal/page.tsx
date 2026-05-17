"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getDriverId, getOrganizationId } from "@/lib/auth";
import {
  DRIVER_WORKFLOW_STEPS,
  checklistFromReadiness,
  documentCompletion,
  getMissingRequiredDocuments,
  nextActionForLoad,
  statusClasses,
  statusLabel,
  toDriverStatus,
  workflowStepState,
} from "@/lib/driver-portal";

type TokenClaims = {
  sub?: string;
  email?: string;
  role?: string;
  driver_id?: string;
  organization_id?: string;
};

type DriverLoad = {
  id: string;
  load_number: string;
  status: string;
  pickup_location: string;
  delivery_location: string;
  broker_name: string | null;
  customer_account_name: string | null;
  pickup_date: string | null;
  delivery_date: string | null;
  packet_readiness: Record<string, unknown> | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asText(value: unknown, fallback = "—"): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asOptionalText(value: unknown): string | null {
  const text = asText(value, "");
  return text || null;
}

function unwrapApiData(payload: unknown): Record<string, unknown> | null {
  const root = asRecord(payload);
  const data = asRecord(root?.data);
  return data ?? root;
}

function listCount(payload: unknown): number {
  const root = asRecord(payload);
  if (Array.isArray(payload)) return payload.length;
  if (!root) return 0;
  const items = Array.isArray(root.data) ? root.data : Array.isArray(root.items) ? root.items : [];
  const meta = asRecord(root.meta);
  const metaTotal = Number(meta?.total);
  return Number.isFinite(metaTotal) && metaTotal >= 0 ? metaTotal : items.length;
}

function normalizeLoads(payload: unknown): DriverLoad[] {
  const root = asRecord(payload);
  const nestedData = asRecord(root?.data);
  const items = Array.isArray(payload)
    ? payload
    : Array.isArray(root?.data)
      ? root.data
      : Array.isArray(nestedData?.items)
        ? nestedData.items
        : Array.isArray(root?.items)
          ? root.items
          : [];

  return items
    .map((item): DriverLoad | null => {
      const record = asRecord(item);
      const id = asOptionalText(record?.id);
      if (!record || !id) return null;
      return {
        id,
        load_number: asText(record.load_number),
        status: asText(record.status, "booked"),
        pickup_location: asText(record.pickup_location),
        delivery_location: asText(record.delivery_location),
        broker_name: asOptionalText(record.broker_name),
        customer_account_name: asOptionalText(record.customer_account_name),
        pickup_date: asOptionalText(record.pickup_date),
        delivery_date: asOptionalText(record.delivery_date),
        packet_readiness: asRecord(record.packet_readiness),
      };
    })
    .filter((item): item is DriverLoad => item !== null);
}

function parseJwtClaims(token: string | null): TokenClaims | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded = typeof window !== "undefined" ? window.atob(padded) : Buffer.from(padded, "base64").toString("utf-8");
    const record = asRecord(JSON.parse(decoded) as unknown);
    if (!record) return null;
    return {
      sub: typeof record.sub === "string" ? record.sub : undefined,
      email: typeof record.email === "string" ? record.email : undefined,
      role: typeof record.role === "string" ? record.role : undefined,
      driver_id: typeof record.driver_id === "string" ? record.driver_id : undefined,
      organization_id: typeof record.organization_id === "string" ? record.organization_id : undefined,
    };
  } catch {
    return null;
  }
}

function formatShortDate(value: string | null): string {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function WorkflowTimeline({ load }: { load: DriverLoad }) {
  const checklist = checklistFromReadiness(load.packet_readiness);
  const states = workflowStepState(load.status, checklist);
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
      {DRIVER_WORKFLOW_STEPS.map((step) => {
        const state = states[step.key];
        return (
          <div key={step.key} className={`rounded-2xl border px-3 py-3 text-xs font-bold ${state === "done" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : state === "current" ? "border-brand-200 bg-brand-50 text-brand-800" : "border-slate-200 bg-slate-50 text-slate-500"}`}>
            <div className="mb-2 h-2 rounded-full bg-current opacity-50" />
            {step.label}
          </div>
        );
      })}
    </div>
  );
}

export default function DriverPortalPage() {
  const [loads, setLoads] = useState<DriverLoad[]>([]);
  const [openTickets, setOpenTickets] = useState<number>(0);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const token = getAccessToken();
  const organizationId = getOrganizationId();
  const claims = useMemo(() => parseJwtClaims(token), [token]);
  const driverId = getDriverId() ?? claims?.driver_id ?? "";
  const driverEmail = claims?.email ?? "";
  const role = claims?.role ?? "";

  useEffect(() => {
    if (!token || !organizationId) {
      setLoads([]);
      setOpenTickets(0);
      setErrorMessage("Your driver session needs to be refreshed before we can show current assignments.");
      return;
    }

    if (role !== "driver") {
      setLoads([]);
      setOpenTickets(0);
      setErrorMessage("This workspace is reserved for driver accounts.");
      return;
    }

    if (!driverId) {
      setLoads([]);
      setOpenTickets(0);
      setErrorMessage("Your driver account is missing an assignment ID. Contact dispatch.");
      return;
    }

    let mounted = true;

    async function loadSummary() {
      try {
        setIsLoadingSummary(true);
        setErrorMessage(null);
        const [loadsPayload, supportPayload] = await Promise.all([
          apiClient.get<unknown>(`/driver/loads?page=1&page_size=10`, { token: token ?? undefined, organizationId: organizationId ?? undefined }),
          apiClient
            .get<unknown>(`/support/tickets?driver_id=${driverId}&status=open&page=1&page_size=1`, { token: token ?? undefined, organizationId: organizationId ?? undefined })
            .catch((error: unknown) => {
              if (error instanceof ApiClientError && [404, 501].includes(error.status)) return { data: [] };
              throw error;
            }),
        ]);

        if (!mounted) return;
        const normalizedLoads = normalizeLoads(loadsPayload);
        if (normalizedLoads[0]?.id) {
          try {
            const activeLoadPayload = await apiClient.get<unknown>(`/driver/loads/${normalizedLoads[0].id}`, {
              token: token ?? undefined,
              organizationId: organizationId ?? undefined,
            });
            const [activeLoadDetail] = normalizeLoads([unwrapApiData(activeLoadPayload)]);
            setLoads(activeLoadDetail ? [activeLoadDetail, ...normalizedLoads.slice(1)] : normalizedLoads);
          } catch {
            setLoads(normalizedLoads);
          }
        } else {
          setLoads(normalizedLoads);
        }
        setOpenTickets(listCount(supportPayload));
      } catch (error: unknown) {
        if (!mounted) return;
        setErrorMessage(error instanceof Error ? error.message : "Dispatch data could not refresh. Your last loaded view remains safe to use.");
      } finally {
        if (mounted) setIsLoadingSummary(false);
      }
    }

    void loadSummary();
    return () => {
      mounted = false;
    };
  }, [token, organizationId, role, driverId]);

  const activeLoad = loads[0] ?? null;
  const activeChecklist = activeLoad ? checklistFromReadiness(activeLoad.packet_readiness) : [];
  const missingRequiredDocs = getMissingRequiredDocuments(activeChecklist);
  const completion = documentCompletion(activeChecklist);
  const nextAction = activeLoad ? nextActionForLoad({ rawStatus: activeLoad.status, checklist: activeChecklist }) : null;
  const driverStatus = activeLoad ? toDriverStatus(activeLoad.status, missingRequiredDocs.length > 0) : "no active load";

  return (
    <main className="safe-page min-h-screen overflow-x-hidden bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6 sm:py-10">
        <section className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-brand-700">Driver Portal</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Today’s operating workspace</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">See your active load, required paperwork, approval state, and the next action dispatch or accounting is waiting on.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 lg:min-w-72">
              <div className="font-bold text-slate-950">Authenticated driver</div>
              <div className="mt-2 truncate">{driverEmail || "—"}</div>
              <div className="mt-1 truncate text-xs">ID: {driverId || "—"}</div>
            </div>
          </div>
        </section>

        {errorMessage ? <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{errorMessage}</div> : null}

        {isLoadingSummary && !activeLoad ? (
          <section className="mt-5 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft">
            <div className="skeleton h-5 w-32 rounded-full bg-slate-200" />
            <div className="skeleton mt-4 h-10 w-3/4 rounded-2xl bg-slate-200" />
            <div className="skeleton mt-4 h-28 rounded-3xl bg-slate-100" />
          </section>
        ) : null}

        {!isLoadingSummary && !activeLoad ? (
          <section className="mt-5 rounded-[2rem] border border-dashed border-slate-300 bg-white p-6 text-center shadow-soft">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-2xl">✓</div>
            <h2 className="mt-4 text-2xl font-bold text-slate-950">No active loads assigned.</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">Dispatch will notify you when a load is available. If you expected an assignment, contact dispatch or open a support request.</p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/driver-portal/support" className="touch-target rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white">Contact support</Link>
              <Link href="/driver-portal/loads" className="touch-target rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-800">View load history</Link>
            </div>
          </section>
        ) : null}

        {activeLoad ? (
          <>
            <section className="mt-5 overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 shadow-soft">
              <div className="bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.35),transparent_35%),linear-gradient(135deg,#020617,#0f172a)] p-5 text-white sm:p-6">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/55">Active Load Focus</p>
                    <h2 className="mt-2 break-words text-3xl font-black tracking-tight sm:text-4xl">Load {activeLoad.load_number}</h2>
                    <p className="mt-3 text-lg font-semibold text-white/90">{activeLoad.pickup_location} → {activeLoad.delivery_location}</p>
                    <p className="mt-2 text-sm text-white/60">{activeLoad.broker_name ?? activeLoad.customer_account_name ?? "Customer details available in load detail"}</p>
                  </div>
                  <div className="rounded-3xl border border-white/15 bg-white/10 p-4 backdrop-blur lg:w-80">
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-black capitalize text-slate-950">{driverStatus}</span>
                      <span className="text-xs font-semibold text-white/70">{completion.completed}/{completion.total} required</span>
                    </div>
                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/15">
                      <div className="h-full rounded-full bg-emerald-400" style={{ width: `${completion.percent}%` }} />
                    </div>
                    <p className="mt-3 text-sm leading-6 text-white/72">Document completion is based on required driver paperwork received for this load.</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="mt-5 grid gap-4 lg:grid-cols-[1fr_1.35fr]">
              <div className={`rounded-[2rem] border p-5 shadow-soft ${nextAction?.tone === "blocked" ? "border-rose-200 bg-rose-50" : nextAction?.tone === "success" ? "border-emerald-200 bg-emerald-50" : nextAction?.tone === "waiting" ? "border-sky-200 bg-sky-50" : "border-amber-200 bg-amber-50"}`}>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-600">Next Action Center</p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">{nextAction?.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-700">{nextAction?.description}</p>
                <Link href={`/driver-portal/loads/${activeLoad.id}`} className="touch-target mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white sm:w-auto">{nextAction?.ctaLabel}</Link>
              </div>

              <div className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.16em] text-brand-700">Document Status Summary</p>
                    <h2 className="mt-1 text-xl font-black text-slate-950">Required paperwork</h2>
                  </div>
                  <Link href={`/driver-portal/loads/${activeLoad.id}#driver-document-uploads-heading`} className="touch-target rounded-xl border border-slate-200 px-3 py-2 text-xs font-black text-slate-700">Upload</Link>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {activeChecklist.filter((item) => item.required).map((item) => (
                    <div key={item.type} className="rounded-2xl border border-slate-200 p-3">
                      <div className="text-sm font-black text-slate-950">{item.label}</div>
                      <span className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-black ${statusClasses(item.status)}`}>{statusLabel(item.status)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="mt-5 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.16em] text-brand-700">Load Timeline</p>
                  <h2 className="mt-1 text-xl font-black text-slate-950">Workflow progression</h2>
                </div>
                <p className="text-sm text-slate-500">Pickup {formatShortDate(activeLoad.pickup_date)} · Delivery {formatShortDate(activeLoad.delivery_date)}</p>
              </div>
              <div className="mt-4">
                <WorkflowTimeline load={activeLoad} />
              </div>
            </section>
          </>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-3">
          <Link href="/driver-portal/loads" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Loads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Open assigned load details, status updates, and paperwork.</p>
          </Link>
          <Link href="/driver-portal/uploads" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Uploads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Send photos or files into the paperwork workflow.</p>
          </Link>
          <Link href="/driver-portal/support" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Support</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Open support requests when a load or document is blocked.</p>
            {openTickets > 0 ? <span className="mt-3 inline-flex rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">{openTickets} open</span> : null}
          </Link>
        </section>
      </div>
    </main>
  );
}
