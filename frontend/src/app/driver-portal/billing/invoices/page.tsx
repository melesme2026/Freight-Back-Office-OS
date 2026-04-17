"use client";

import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type Invoice = {
  id: string;
  invoice_number?: string | null;
  status?: string | null;
  total_amount?: string | number | null;
  amount_due?: string | number | null;
  currency_code?: string | null;
  due_at?: string | null;
  issued_at?: string | null;
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

function formatMoney(value: string | number | null | undefined, currencyCode?: string | null): string {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currencyCode || "USD" }).format(numeric);
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("en-US");
}

function statusBadge(status: string): string {
  switch (status) {
    case "paid":
      return "bg-emerald-100 text-emerald-800";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    case "open":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function DriverBillingInvoicesPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  const token = getAccessToken();
  const organizationId = getOrganizationId();
  const driverId = useMemo(() => parseDriverId(token), [token]);

  useEffect(() => {
    if (!token || !organizationId || !driverId) {
      setIsLoading(false);
      setErrorMessage("Missing driver billing context.");
      return;
    }

    let mounted = true;

    async function loadInvoices() {
      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient.get(`/billing-invoices?driver_id=${driverId}&page=1&page_size=50`, {
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
              invoice_number: typeof row.invoice_number === "string" ? row.invoice_number : null,
              status: typeof row.status === "string" ? row.status.toLowerCase() : "unknown",
              total_amount: (row.total_amount as string | number | null | undefined) ?? null,
              amount_due: (row.amount_due as string | number | null | undefined) ?? null,
              currency_code: typeof row.currency_code === "string" ? row.currency_code : "USD",
              due_at: typeof row.due_at === "string" ? row.due_at : null,
              issued_at: typeof row.issued_at === "string" ? row.issued_at : null,
            } as Invoice;
          })
          .filter((item): item is Invoice => item !== null);

        if (mounted) {
          setInvoices(normalized);
        }
      } catch (error) {
        if (mounted) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load invoices.");
          setInvoices([]);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void loadInvoices();
    return () => {
      mounted = false;
    };
  }, [driverId, organizationId, token]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing / Invoices</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">My Invoices</h1>
        </div>

        {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Invoice</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Total</th>
                  <th className="px-5 py-4 font-semibold">Amount Due</th>
                  <th className="px-5 py-4 font-semibold">Issued</th>
                  <th className="px-5 py-4 font-semibold">Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-500">Loading invoices...</td></tr>
                ) : invoices.length === 0 ? (
                  <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-500">No driver-linked invoices found.</td></tr>
                ) : (
                  invoices.map((invoice) => (
                    <tr key={invoice.id}>
                      <td className="px-5 py-4"><div className="font-semibold text-slate-900">{invoice.invoice_number || invoice.id}</div></td>
                      <td className="px-5 py-4"><span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge((invoice.status || "unknown").toLowerCase())}`}>{(invoice.status || "unknown").replaceAll("_", " ")}</span></td>
                      <td className="px-5 py-4">{formatMoney(invoice.total_amount, invoice.currency_code)}</td>
                      <td className="px-5 py-4">{formatMoney(invoice.amount_due, invoice.currency_code)}</td>
                      <td className="px-5 py-4">{formatDate(invoice.issued_at)}</td>
                      <td className="px-5 py-4">{formatDate(invoice.due_at)}</td>
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
