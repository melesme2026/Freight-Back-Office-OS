"use client";

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type Payment = {
  id: string;
  status: string;
  amount?: string | number | null;
  currency_code?: string | null;
  provider?: string | null;
  attempted_at?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function parseDriverId(token: string | null): string {
  if (!token) return "";
  try {
    const payload = token.split(".")[1];
    if (!payload) return "";
    const decoded = JSON.parse(window.atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof decoded.driver_id === "string" ? decoded.driver_id : "";
  } catch {
    return "";
  }
}

function statusBadge(status: string): string {
  switch (status) {
    case "succeeded":
      return "bg-emerald-100 text-emerald-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    case "pending":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function formatMoney(value: string | number | null | undefined, currencyCode?: string | null): string {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currencyCode || "USD" }).format(numeric);
}

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("en-US");
}

export default function DriverBillingPaymentsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);

  const token = getAccessToken();
  const organizationId = getOrganizationId();
  const driverId = useMemo(() => parseDriverId(token), [token]);

  useEffect(() => {
    if (!token || !organizationId || !driverId) {
      setIsLoading(false);
      setErrorMessage("Missing driver payment context.");
      return;
    }

    let mounted = true;

    async function loadPayments() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient.get(`/payments?driver_id=${driverId}&page=1&page_size=50`, {
          token: token ?? undefined,
          organizationId: organizationId ?? undefined,
        });

        const root = asRecord(payload);
        const list = Array.isArray(root?.data) ? root.data : [];

        const normalized = list
          .map((item) => {
            const row = asRecord(item);
            if (!row || typeof row.id !== "string") return null;
            return {
              id: row.id,
              status: typeof row.status === "string" ? row.status.toLowerCase() : "unknown",
              amount: (row.amount as string | number | null | undefined) ?? null,
              currency_code: typeof row.currency_code === "string" ? row.currency_code : "USD",
              provider: typeof row.provider === "string" ? row.provider : null,
              attempted_at: typeof row.attempted_at === "string" ? row.attempted_at : null,
            } as Payment;
          })
          .filter((item): item is Payment => item !== null);

        if (mounted) {
          setPayments(normalized);
        }
      } catch (error) {
        if (mounted) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load payments.");
          setPayments([]);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadPayments();
    return () => {
      mounted = false;
    };
  }, [driverId, organizationId, token]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing / Payments</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">My Payments</h1>
        </div>

        {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Payment ID</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                  <th className="px-5 py-4 font-semibold">Provider</th>
                  <th className="px-5 py-4 font-semibold">Attempted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">Loading payments...</td></tr>
                ) : payments.length === 0 ? (
                  <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">No driver-linked payments found.</td></tr>
                ) : (
                  payments.map((payment) => (
                    <tr key={payment.id}>
                      <td className="px-5 py-4 font-semibold text-slate-900">{payment.id}</td>
                      <td className="px-5 py-4"><span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(payment.status)}`}>{payment.status.replaceAll("_", " ")}</span></td>
                      <td className="px-5 py-4">{formatMoney(payment.amount, payment.currency_code)}</td>
                      <td className="px-5 py-4">{payment.provider || "—"}</td>
                      <td className="px-5 py-4">{formatDateTime(payment.attempted_at)}</td>
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
