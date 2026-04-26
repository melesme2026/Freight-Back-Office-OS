"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { toDriverStatus } from "@/lib/driver-portal";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type DriverLoad = {
  id: string;
  load_number: string;
  status: string;
  pickup_location: string;
  delivery_location: string;
  missing_documents: string[];
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

function normalizeLoads(payload: unknown): DriverLoad[] {
  const root = asRecord(payload);
  const items = Array.isArray(root?.data) ? root.data : [];

  return items
    .map((item) => {
      const record = asRecord(item);
      if (!record) return null;
      const packetReadiness = asRecord(record.packet_readiness);
      const missingRequired = asRecord(packetReadiness?.missing_required_documents);
      const missingSubmission = Array.isArray(missingRequired?.submission)
        ? missingRequired?.submission.filter((item) => typeof item === "string")
        : [];

      const id = asText(record.id, "");
      if (!id) return null;

      return {
        id,
        load_number: asText(record.load_number),
        status: asText(record.status, "booked"),
        pickup_location: asText(record.pickup_location),
        delivery_location: asText(record.delivery_location),
        missing_documents: missingSubmission,
      };
    })
    .filter((item): item is DriverLoad => item !== null);
}

export default function DriverLoadsPage() {
  const [loads, setLoads] = useState<DriverLoad[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId) {
      setLoads([]);
      setIsLoading(false);
      return;
    }

    let mounted = true;

    async function loadDriverLoads() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient.get<unknown>("/driver/loads?page=1&page_size=50", {
          token: token ?? undefined,
          organizationId: organizationId ?? undefined,
        });

        if (!mounted) return;
        setLoads(normalizeLoads(payload));
      } catch (error: unknown) {
        if (!mounted) return;
        setLoads([]);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load driver loads.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadDriverLoads();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <div className="mb-6">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Loads</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">My Loads</h1>
        </div>

        {errorMessage ? <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}

        <section className="space-y-3">
          {isLoading ? <div className="rounded-2xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">Loading loads...</div> : null}
          {!isLoading && loads.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">No loads found for this driver.</div> : null}

          {loads.map((load) => {
            const status = toDriverStatus(load.status, load.missing_documents.length > 0);
            return (
              <Link key={load.id} href={`/driver-portal/loads/${load.id}`} className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                <div className="text-base font-semibold text-slate-900">{load.load_number}</div>
                <div className="mt-1 text-sm text-slate-600">{load.pickup_location} → {load.delivery_location}</div>
                <div className="mt-2 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold capitalize text-slate-700">Status: {status}</div>
                {load.missing_documents.length > 0 ? (
                  <div className="mt-3 text-sm font-medium text-amber-700">⚠ Missing: {load.missing_documents.join(", ")}</div>
                ) : null}
              </Link>
            );
          })}
        </section>
      </div>
    </main>
  );
}
