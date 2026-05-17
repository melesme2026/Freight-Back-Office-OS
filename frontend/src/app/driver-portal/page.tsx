"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getDriverId, getOrganizationId } from "@/lib/auth";

type TokenClaims = {
  sub?: string;
  email?: string;
  role?: string;
  driver_id?: string;
  organization_id?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
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

function SummaryCard({ label, value, helper, loading }: { label: string; value: number; helper: string; loading: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</div>
      {loading ? <div className="skeleton mt-3 h-9 w-20 rounded-xl bg-slate-200" /> : <div className="mt-2 text-3xl font-bold text-slate-950">{value}</div>}
      <div className="mt-2 text-xs leading-5 text-slate-500">{helper}</div>
    </div>
  );
}

export default function DriverPortalPage() {
  const [openLoads, setOpenLoads] = useState<number>(0);
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
      setOpenLoads(0);
      setOpenTickets(0);
      setErrorMessage("Missing authenticated session.");
      return;
    }

    if (role !== "driver") {
      setOpenLoads(0);
      setOpenTickets(0);
      setErrorMessage("Driver portal requires an authenticated driver session.");
      return;
    }

    if (!driverId) {
      setOpenLoads(0);
      setOpenTickets(0);
      setErrorMessage("Missing driver_id in authenticated session.");
      return;
    }

    let mounted = true;

    async function loadSummary() {
      try {
        setIsLoadingSummary(true);
        setErrorMessage(null);
        const [loadsPayload, supportPayload] = await Promise.all([
          apiClient.get<unknown>(`/driver/loads?page=1&page_size=1`, { token: token ?? undefined, organizationId: organizationId ?? undefined }),
          apiClient
            .get<unknown>(`/support/tickets?driver_id=${driverId}&status=open&page=1&page_size=1`, { token: token ?? undefined, organizationId: organizationId ?? undefined })
            .catch((error: unknown) => {
              if (error instanceof ApiClientError && [404, 501].includes(error.status)) return { data: [] };
              throw error;
            }),
        ]);

        if (!mounted) return;
        setOpenLoads(listCount(loadsPayload));
        setOpenTickets(listCount(supportPayload));
      } catch (error: unknown) {
        if (!mounted) return;
        setOpenLoads(0);
        setOpenTickets(0);
        setErrorMessage(error instanceof Error ? error.message : "Couldn’t refresh driver summary.");
      } finally {
        if (mounted) setIsLoadingSummary(false);
      }
    }

    void loadSummary();
    return () => {
      mounted = false;
    };
  }, [token, organizationId, role, driverId]);

  const nextAction = openLoads > 0 ? "Review active load details and upload any missing paperwork." : "No active load is assigned. Contact dispatch if you expected one.";
  const uploadProgress = openLoads > 0 ? "POD is the usual final document before billing can submit the packet." : "Uploads become available as soon as dispatch assigns a load.";

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-brand-700">Driver Portal</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Driver Workspace</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">A simple operating view for assigned loads, required uploads, and support help.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 lg:min-w-72">
              <div className="font-bold text-slate-950">Authenticated driver</div>
              <div className="mt-2 truncate">{driverEmail || "—"}</div>
              <div className="mt-1 truncate text-xs">ID: {driverId || "—"}</div>
            </div>
          </div>
        </section>

        {errorMessage ? <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Couldn’t refresh driver summary. Navigation and uploads remain available.</div> : null}

        <section className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-soft sm:p-6">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-white/60">Active Load</h2>
            <div className="mt-2 text-xl font-bold">{isLoadingSummary ? "Checking assignment" : openLoads > 0 ? `${openLoads} assigned load${openLoads === 1 ? "" : "s"}` : "No active load"}</div>
            <p className="mt-2 text-sm leading-6 text-white/70">{nextAction}</p>
            <Link href="/driver-portal/loads" className="touch-target mt-4 inline-flex items-center rounded-xl bg-white px-4 py-2 text-sm font-bold text-slate-950">Open loads</Link>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-brand-700">Next Required Action</h2>
            <div className="mt-2 text-xl font-bold text-slate-950">Upload progression</div>
            <p className="mt-2 text-sm leading-6 text-slate-600">{uploadProgress}</p>
            <div className="mt-4 grid gap-2 text-xs font-semibold text-slate-600">
              <div className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-700">Completed: rate confirmation and BOL when provided by dispatch</div>
              <div className="rounded-xl bg-amber-50 px-3 py-2 text-amber-700">Missing: POD or load-specific documents after delivery</div>
              <div className="rounded-xl bg-slate-50 px-3 py-2 text-slate-600">Timeline-ready: pickup, in-transit, delivered, paperwork received</div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-4 md:grid-cols-2">
          <SummaryCard label="Driver loads" value={openLoads} helper="Assigned work visible to this driver." loading={isLoadingSummary} />
          <SummaryCard label="Open support" value={openTickets} helper="Unresolved help requests." loading={isLoadingSummary} />
        </section>

        <section className="mt-8 grid gap-4 md:grid-cols-3">
          <Link href="/driver-portal/loads" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Loads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">See assignments, status, stops, and load detail actions.</p>
          </Link>
          <Link href="/driver-portal/uploads" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Uploads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Send photos or files into the paperwork workflow.</p>
          </Link>
          <Link href="/driver-portal/support" className="touch-target rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:border-brand-300 hover:bg-brand-50">
            <h2 className="text-base font-bold text-slate-950">Support</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Ask dispatch or back office for help on blockers.</p>
          </Link>
        </section>
      </div>
    </main>
  );
}
