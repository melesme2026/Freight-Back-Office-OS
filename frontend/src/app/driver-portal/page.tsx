"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useDrivers } from "@/hooks/useDrivers";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

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

export default function DriverPortalPage() {
  const { drivers, isLoading: isDriverLoading, error: driverError } = useDrivers();
  const [selectedDriverId, setSelectedDriverId] = useState<string>("");
  const [openLoads, setOpenLoads] = useState<number>(0);
  const [openTickets, setOpenTickets] = useState<number>(0);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDriverId && drivers.length > 0) {
      setSelectedDriverId(drivers[0].id);
    }
  }, [drivers, selectedDriverId]);

  useEffect(() => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!selectedDriverId || !organizationId) {
      setOpenLoads(0);
      setOpenTickets(0);
      return;
    }

    let mounted = true;

    async function loadSummary() {
      try {
        setIsLoadingSummary(true);
        setErrorMessage(null);

        const [loadsPayload, supportPayload] = await Promise.all([
          apiClient.get<unknown>(`/loads?driver_id=${selectedDriverId}&status=in_transit&page=1&page_size=1`, {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }),
          apiClient.get<unknown>(
            `/support/tickets?driver_id=${selectedDriverId}&status=open&page=1&page_size=1`,
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
  }, [selectedDriverId]);

  const selectedDriver = useMemo(
    () => drivers.find((driver) => driver.id === selectedDriverId) ?? null,
    [drivers, selectedDriverId]
  );

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

        {driverError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {driverError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <label htmlFor="driver-select" className="text-sm font-semibold text-slate-700">
            Driver
          </label>
          <select
            id="driver-select"
            value={selectedDriverId}
            onChange={(event) => setSelectedDriverId(event.target.value)}
            disabled={isDriverLoading || drivers.length === 0}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {drivers.length === 0 ? <option value="">No drivers available</option> : null}
            {drivers.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.full_name}
              </option>
            ))}
          </select>
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-sm text-slate-500">Open loads (in transit)</div>
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
          <Link href="/driver-portal/loads" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-base font-semibold text-slate-950">Loads</h2>
            <p className="mt-2 text-sm text-slate-600">Driver-scoped load list preview.</p>
          </Link>
          <Link href="/driver-portal/uploads" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-base font-semibold text-slate-950">Uploads</h2>
            <p className="mt-2 text-sm text-slate-600">Upload documents into real processing flow.</p>
          </Link>
          <Link href="/driver-portal/support" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-base font-semibold text-slate-950">Support</h2>
            <p className="mt-2 text-sm text-slate-600">View driver-related support tickets.</p>
          </Link>
          <Link href="/driver-portal/billing" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-base font-semibold text-slate-950">Billing</h2>
            <p className="mt-2 text-sm text-slate-600">
              Billing visibility status and currently supported scope.
            </p>
          </Link>
        </section>

        {selectedDriver ? (
          <p className="mt-6 text-xs text-slate-500">
            Previewing as: {selectedDriver.full_name} ({selectedDriver.id})
          </p>
        ) : null}
      </div>
    </main>
  );
}
