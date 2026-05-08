"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

type ApiResponse<T> = { data: T; meta?: Record<string, unknown>; error?: { message?: string } | null };
type FactoringCompany = {
  id: string;
  company_name: string;
  contact_email?: string | null;
  phone?: string | null;
  notes?: string | null;
  default_reserve_percent?: string | null;
  default_fee_percent?: string | null;
};
type FactoringRecord = {
  id: string;
  load_id: string;
  factor_name?: string | null;
  factoring_company_name?: string | null;
  factoring_status?: string | null;
  reconciliation_status?: string | null;
  aging_bucket?: string | null;
  expected_amount?: string | null;
  advance_amount?: string | null;
  reserve_amount?: string | null;
  reserve_pending_amount?: string | null;
  factoring_fee_amount?: string | null;
  amount_received?: string | null;
  currency?: string | null;
  factoring_notes?: string | null;
};

const defaultCompany = {
  company_name: "",
  contact_email: "",
  phone: "",
  notes: "",
  default_reserve_percent: "",
  default_fee_percent: "",
};

function money(value?: string | null, currency = "USD") {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number.isFinite(amount) ? amount : 0);
}

function label(value?: string | null) {
  return (value ?? "—").replaceAll("_", " ");
}

export default function FactoringDashboardPage() {
  const [companies, setCompanies] = useState<FactoringCompany[]>([]);
  const [records, setRecords] = useState<FactoringRecord[]>([]);
  const [form, setForm] = useState(defaultCompany);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const auth = useMemo(() => ({ token: getAccessToken(), organizationId: getOrganizationId() }), []);

  async function refresh() {
    if (!auth.token || !auth.organizationId) return;
    const [companyResponse, dashboardResponse] = await Promise.all([
      apiClient.get<ApiResponse<FactoringCompany[]>>("/factoring-companies", { token: auth.token, organizationId: auth.organizationId }),
      apiClient.get<ApiResponse<FactoringRecord[]>>("/factoring-dashboard", { token: auth.token, organizationId: auth.organizationId }),
    ]);
    setCompanies(companyResponse.data ?? []);
    setRecords(dashboardResponse.data ?? []);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load factoring dashboard."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.company_name.trim()) {
      setError("Company name is required.");
      return;
    }
    if (!auth.token || !auth.organizationId) {
      setError("Sign in again to manage factoring companies.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await apiClient.post<ApiResponse<FactoringCompany>>("/factoring-companies", {
          company_name: form.company_name,
          contact_email: form.contact_email || null,
          phone: form.phone || null,
          notes: form.notes || null,
          default_reserve_percent: form.default_reserve_percent || null,
          default_fee_percent: form.default_fee_percent || null,
        },
        { token: auth.token, organizationId: auth.organizationId }
      );
      setForm(defaultCompany);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save factoring company.");
    } finally {
      setIsSaving(false);
    }
  }

  const totals = records.reduce(
    (acc, record) => {
      acc.expected += Number(record.expected_amount ?? 0) || 0;
      acc.advance += Number(record.advance_amount ?? 0) || 0;
      acc.reservePending += Number(record.reserve_pending_amount ?? 0) || 0;
      return acc;
    },
    { expected: 0, advance: 0, reservePending: 0 }
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">Operational factoring</p>
          <h1 className="text-2xl font-bold text-slate-950">Factoring workflow dashboard</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">Track factoring companies, funded advances, reserves, fees, reconciliation state, aging, and operational notes without adding ERP/accounting scope.</p>
        </div>
      </div>

      {error ? <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft"><p className="text-xs uppercase text-slate-500">Factored exposure</p><p className="mt-2 text-2xl font-bold text-slate-950">{money(String(totals.expected))}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft"><p className="text-xs uppercase text-slate-500">Advances funded</p><p className="mt-2 text-2xl font-bold text-slate-950">{money(String(totals.advance))}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft"><p className="text-xs uppercase text-slate-500">Reserve pending</p><p className="mt-2 text-2xl font-bold text-amber-700">{money(String(totals.reservePending))}</p></div>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
        <form onSubmit={submitCompany} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">Add factoring company</h2>
          <div className="mt-4 grid gap-3">
            {Object.entries(form).map(([key, value]) => (
              <label key={key} className="text-sm font-medium text-slate-700">
                {label(key)}
                <input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-base sm:text-sm" value={value} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />
              </label>
            ))}
          </div>
          <button disabled={isSaving} className="mt-4 w-full rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{isSaving ? "Saving..." : "Save company"}</button>
          <div className="mt-5 space-y-2">
            {companies.map((company) => (
              <div key={company.id} className="rounded-xl border border-slate-200 px-3 py-2 text-sm">
                <div className="font-semibold text-slate-900">{company.company_name}</div>
                <div className="text-slate-600">Reserve {company.default_reserve_percent ?? "0"}% · Fee {company.default_fee_percent ?? "0"}%</div>
              </div>
            ))}
          </div>
        </form>

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="border-b border-slate-200 p-4 sm:p-6"><h2 className="text-lg font-semibold text-slate-950">Factored loads</h2><p className="text-sm text-slate-600">Open each load for assignment, payment, reserve, fee, reconciliation, and note updates.</p></div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Factor</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Aging</th><th className="px-4 py-3">Advance</th><th className="px-4 py-3">Reserve Pending</th><th className="px-4 py-3">Notes</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {records.map((record) => (
                  <tr key={record.id} className="align-top">
                    <td className="px-4 py-3 font-medium text-slate-900">{record.factoring_company_name ?? record.factor_name ?? "—"}</td>
                    <td className="px-4 py-3"><div>{label(record.factoring_status)}</div><div className="text-xs text-slate-500">{label(record.reconciliation_status)}</div></td>
                    <td className="px-4 py-3">{label(record.aging_bucket)}</td>
                    <td className="px-4 py-3">{money(record.advance_amount, record.currency ?? "USD")}</td>
                    <td className="px-4 py-3">{money(record.reserve_pending_amount, record.currency ?? "USD")}</td>
                    <td className="max-w-xs px-4 py-3 text-slate-600">{record.factoring_notes ?? "—"}</td>
                  </tr>
                ))}
                {records.length === 0 ? <tr><td className="px-4 py-8 text-center text-slate-500" colSpan={6}>No factored loads yet.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
