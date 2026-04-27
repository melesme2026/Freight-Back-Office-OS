"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getDriverId, getOrganizationId } from "@/lib/auth";

type SupportTicket = {
  id: string;
  subject: string;
  status: string;
  priority: string;
};

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

function asText(value: unknown, fallback = "—"): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
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
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const token = getAccessToken();
  const organizationId = getOrganizationId();

  const claims = useMemo(() => parseJwtClaims(token), [token]);
  const driverId = getDriverId() ?? claims?.driver_id ?? "";
  const driverEmail = claims?.email ?? "";
  const role = claims?.role ?? "";

  useEffect(() => {
    if (!token || !organizationId) {
      setTickets([]);
      setIsLoading(false);
      setErrorMessage("Missing authenticated session.");
      return;
    }

    if (role !== "driver") {
      setTickets([]);
      setIsLoading(false);
      setErrorMessage("Driver portal requires an authenticated driver session.");
      return;
    }

    if (!driverId) {
      setTickets([]);
      setIsLoading(false);
      setErrorMessage("Missing driver_id in authenticated session.");
      return;
    }

    let mounted = true;

    async function loadTickets() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient
          .get<unknown>(`/support/tickets?driver_id=${driverId}&page=1&page_size=50`, {
            token: token ?? undefined,
            organizationId: organizationId ?? undefined,
          })
          .catch((error: unknown) => {
            if (error instanceof ApiClientError && [404, 501].includes(error.status)) {
              return { data: [] };
            }
            throw error;
          });

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
  }, [token, organizationId, role, driverId]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Support</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support Tickets</h1>
          <p className="mt-2 text-sm text-slate-600">
            Authenticated driver support tickets only.
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
