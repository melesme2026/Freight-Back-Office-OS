"use client";

import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type DriverLoad = {
  id: string;
  load_number: string;
  status: string;
  pickup_location: string;
  delivery_location: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asText(value: unknown, fallback = "—"): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

function normalizeLoads(payload: unknown): DriverLoad[] {
  const root = asRecord(payload);
  const items = Array.isArray(root?.data)
    ? root.data
    : Array.isArray(root?.items)
      ? root.items
      : [];

  return items
    .map((item) => {
      const record = asRecord(item);
      if (!record) return null;
      const id = asText(record.id, "");
      if (!id) return null;
      return {
        id,
        load_number: asText(record.load_number),
        status: asText(record.status, "unknown"),
        pickup_location: asText(record.pickup_location),
        delivery_location: asText(record.delivery_location),
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

        const payload = await apiClient.get<unknown>(
          "/loads?page=1&page_size=50",
          {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }
        );

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
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Loads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">My Loads</h1>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-soft">
          Showing loads assigned to your driver account.
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Load #</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Pickup</th>
                  <th className="px-5 py-4 font-semibold">Delivery</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-slate-500">
                      Loading loads...
                    </td>
                  </tr>
                ) : loads.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-slate-500">
                      No loads found for this driver.
                    </td>
                  </tr>
                ) : (
                  loads.map((load) => (
                    <tr key={load.id}>
                      <td className="px-5 py-4 text-slate-900">{load.load_number}</td>
                      <td className="px-5 py-4 text-slate-700">{load.status}</td>
                      <td className="px-5 py-4 text-slate-700">{load.pickup_location}</td>
                      <td className="px-5 py-4 text-slate-700">{load.delivery_location}</td>
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
