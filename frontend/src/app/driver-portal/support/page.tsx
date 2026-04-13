"use client";

import { useEffect, useState } from "react";

import { useDrivers } from "@/hooks/useDrivers";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type SupportTicket = {
  id: string;
  subject: string;
  status: string;
  priority: string;
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

function normalizeTickets(payload: unknown): SupportTicket[] {
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
        subject: asText(record.subject, "Untitled ticket"),
        status: asText(record.status, "unknown"),
        priority: asText(record.priority, "normal"),
      };
    })
    .filter((item): item is SupportTicket => item !== null);
}

export default function DriverSupportPage() {
  const { drivers, isLoading: isDriverLoading, error: driverError } = useDrivers();
  const [selectedDriverId, setSelectedDriverId] = useState("");
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
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
      setTickets([]);
      setIsLoading(false);
      return;
    }

    let mounted = true;

    async function loadTickets() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient.get<unknown>(
          `/support/tickets?driver_id=${selectedDriverId}&page=1&page_size=50`,
          {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          }
        );

        if (!mounted) return;
        setTickets(normalizeTickets(payload));
      } catch (error: unknown) {
        if (!mounted) return;
        setTickets([]);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load support tickets.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadTickets();

    return () => {
      mounted = false;
    };
  }, [selectedDriverId]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Support</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support Tickets</h1>
        </div>

        {driverError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {driverError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <label htmlFor="support-driver-select" className="text-sm font-semibold text-slate-700">
            Driver
          </label>
          <select
            id="support-driver-select"
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

        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Subject</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-8 text-center text-slate-500">
                      Loading support tickets...
                    </td>
                  </tr>
                ) : tickets.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-5 py-8 text-center text-slate-500">
                      No tickets found for this driver.
                    </td>
                  </tr>
                ) : (
                  tickets.map((ticket) => (
                    <tr key={ticket.id}>
                      <td className="px-5 py-4 text-slate-900">
                        <div>{ticket.subject}</div>
                        <div className="text-xs text-slate-500">{ticket.id}</div>
                      </td>
                      <td className="px-5 py-4 text-slate-700">{ticket.status}</td>
                      <td className="px-5 py-4 text-slate-700">{ticket.priority}</td>
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
