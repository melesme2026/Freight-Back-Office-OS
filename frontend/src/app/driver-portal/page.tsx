"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type TokenClaims = {
  sub?: string;
  email?: string;
  role?: string;
  driver_id?: string;
  organization_id?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function listCount(payload: unknown): number {
  const root = asRecord(payload);

  if (Array.isArray(payload)) {
    return payload.length;
  }

  if (!root) {
    return 0;
  }

  const items = Array.isArray(root.data)
    ? root.data
    : Array.isArray(root.items)
      ? root.items
      : [];
  const meta = asRecord(root.meta);
  const metaTotal = Number(meta?.total);

  if (Number.isFinite(metaTotal) && metaTotal >= 0) {
    return metaTotal;
  }

  return items.length;
}

function parseJwtClaims(token: string | null): TokenClaims | null {
  if (!token) {
    return null;
  }

  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const decoded =
      typeof window !== "undefined"
        ? window.atob(padded)
        : Buffer.from(padded, "base64").toString("utf-8");

    const parsed = JSON.parse(decoded) as unknown;
    const record = asRecord(parsed);

    if (!record) {
      return null;
    }

    return {
      sub: typeof record.sub === "string" ? record.sub : undefined,
      email: typeof record.email === "string" ? record.email : undefined,
      role: typeof record.role === "string" ? record.role : undefined,
      driver_id: typeof record.driver_id === "string" ? record.driver_id : undefined,
      organization_id:
        typeof record.organization_id === "string" ? record.organization_id : undefined,
    };
  } catch {
    return null;
  }
}

export default function DriverPortalPage() {
  const [openLoads, setOpenLoads] = useState<number>(0);
  const [openTickets, setOpenTickets] = useState<number>(0);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const token = getAccessToken();
  const organizationId = getOrganizationId();

  const claims = useMemo(() => parseJwtClaims(token), [token]);
  const driverId = claims?.driver_id ?? "";
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
          apiClient.get<unknown>(`/loads?driver_id=${driverId}&page=1&page_size=1`, {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }),
          apiClient.get<unknown>(
            `/support/tickets?driver_id=${driverId}&status=open&page=1&page_size=1`,
            {
              token: token ?? undefined,
              organizationId: organizationId ?? undefined,
            }
          ),
        ]);

        if (!mounted) {
          return;
        }

        setOpenLoads(listCount(loadsPayload));
        setOpenTickets(listCount(supportPayload));
      } catch (error: unknown) {
        if (!mounted) {
          return;
        }

        setOpenLoads(0);
        setOpenTickets(0);
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load driver portal summary."
        );
      } finally {
        if (mounted) {
          setIsLoadingSummary(false);
        }
      }
    }

    void loadSummary();

    return () => {
      mounted = false;
    };
  }, [token, organizationId, role, driverId]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Driver Workspace</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Preview driver-scoped loads, support tickets, and upload workflows backed by existing
            APIs.
          </p>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="text-sm font-semibold text-slate-700">Authenticated driver</div>
          <div className="mt-3 space-y-1 text-sm text-slate-600">
            <p>
              <span className="font-medium text-slate-800">Email:</span>{" "}
              {driverEmail || "—"}
            </p>
            <p>
              <span className="font-medium text-slate-800">Driver ID:</span>{" "}
              {driverId || "—"}
            </p>
          </div>
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-sm text-slate-500">Driver loads</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoadingSummary ? "..." : openLoads}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-sm text-slate-500">Open support tickets</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoadingSummary ? "..." : openTickets}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Link
            href="/driver-portal/loads"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
          >
            <h2 className="text-base font-semibold text-slate-950">Loads</h2>
            <p className="mt-2 text-sm text-slate-600">Driver-scoped load list and status tracking.</p>
          </Link>
          <Link
            href="/driver-portal/uploads"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
          >
            <h2 className="text-base font-semibold text-slate-950">Uploads</h2>
            <p className="mt-2 text-sm text-slate-600">Upload documents into real processing flow.</p>
          </Link>
          <Link
            href="/driver-portal/support"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
          >
            <h2 className="text-base font-semibold text-slate-950">Support</h2>
            <p className="mt-2 text-sm text-slate-600">View driver-related support tickets.</p>
          </Link>
          <Link
            href="/driver-portal/billing"
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
          >
            <h2 className="text-base font-semibold text-slate-950">Billing</h2>
            <p className="mt-2 text-sm text-slate-600">
              Billing visibility status and currently supported scope.
            </p>
          </Link>
        </section>

        {driverId ? (
          <p className="mt-6 text-xs text-slate-500">
            Authenticated as driver ID: {driverId}
          </p>
        ) : null}
      </div>
    </main>
  );
}