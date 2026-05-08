"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  downloadAccountingExport,
  getAccountingSettings,
  updateAccountingSettings,
  type AccountingExportKind,
  type AccountingSettings,
} from "@/lib/accounting";
import { getUserRole } from "@/lib/auth";
import { isDriverRole } from "@/lib/rbac";

const EXPORTS: Array<{ kind: AccountingExportKind; title: string; description: string }> = [
  { kind: "invoices", title: "Invoices", description: "Invoice, load, broker/customer, status, date, and bookkeeping category columns." },
  { kind: "factoring", title: "Factoring activity", description: "Factoring company, funded, reserve, fee, status, and reconciliation columns." },
  { kind: "settlements", title: "Settlements", description: "Invoice totals, deductions, reserve held/released, partial payments, and balance." },
  { kind: "payments", title: "Payments", description: "Paid and partially paid activity prepared for spreadsheet reconciliation." },
  { kind: "aging", title: "Aging/reconciliation", description: "Aging buckets plus reconciliation balances for follow-up and accountant review." },
];

const DEFAULT_MAPPING = {
  accounting_category: "Freight Operations",
  revenue_category: "Freight Revenue",
  factoring_category: "Factoring",
  settlement_category: "Settlements",
  payment_category: "Customer Payments",
};

export default function AccountingExportsPage() {
  const [settings, setSettings] = useState<AccountingSettings | null>(null);
  const [mapping, setMapping] = useState(DEFAULT_MAPPING);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState("");
  const [reconciliationStatus, setReconciliationStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exportingKind, setExportingKind] = useState<AccountingExportKind | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const next = await getAccountingSettings();
        setSettings(next);
        setMapping(next.mapping);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Unable to load accounting exports.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (isDriverRole(getUserRole())) {
    return <div className="p-6 text-sm text-rose-700">Drivers cannot access accounting exports.</div>;
  }

  async function saveMapping(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setSaving(true);
      setError(null);
      const next = await updateAccountingSettings({ mapping });
      setSettings(next);
      setMapping(next.mapping);
      setMessage("Accounting mappings saved.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to save accounting mappings.");
    } finally {
      setSaving(false);
    }
  }

  async function exportCsv(kind: AccountingExportKind) {
    try {
      setExportingKind(kind);
      setError(null);
      await downloadAccountingExport(kind, {
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        status: status || undefined,
        reconciliationStatus: reconciliationStatus || undefined,
      });
      setMessage(`${kind.replaceAll("_", " ")} export generated.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to generate export.");
    } finally {
      setExportingKind(null);
    }
  }

  return (
    <div className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-soft lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">Accounting interoperability</p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">Accounting exports and QuickBooks foundation</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Export freight financial data for accountants, spreadsheets, and QuickBooks import workflows without adding a full ledger or ERP system.
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
            <div className="font-semibold text-slate-950">QuickBooks status</div>
            <div className="mt-1">Mode: {settings?.quickbooks.sync_mode ?? "export_ready"}</div>
            <div>Direct push: {settings?.quickbooks_capabilities.supports_direct_push ? "Enabled" : "Not enabled"}</div>
          </div>
        </header>

        {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
        {message ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div> : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">Export filters</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <label className="text-sm font-medium text-slate-700">From date<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
            <label className="text-sm font-medium text-slate-700">To date<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
            <label className="text-sm font-medium text-slate-700">Payment status<input type="text" placeholder="paid, partially_paid…" value={status} onChange={(event) => setStatus(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
            <label className="text-sm font-medium text-slate-700">Reconciliation<input type="text" placeholder="reconciled…" value={reconciliationStatus} onChange={(event) => setReconciliationStatus(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {EXPORTS.map((item) => (
            <article key={item.kind} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">{item.title}</h2>
              <p className="mt-2 min-h-12 text-sm leading-6 text-slate-600">{item.description}</p>
              <button
                type="button"
                disabled={loading || exportingKind === item.kind}
                onClick={() => void exportCsv(item.kind)}
                className="mt-4 w-full rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {exportingKind === item.kind ? "Generating…" : "Download CSV"}
              </button>
            </article>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <form onSubmit={saveMapping} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">Accounting mappings</h2>
            <p className="mt-2 text-sm text-slate-600">Simple configurable categories are stamped onto exports. This is intentionally not a chart-of-accounts editor.</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {Object.entries(mapping).map(([key, value]) => (
                <label key={key} className="text-sm font-medium capitalize text-slate-700">
                  {key.replaceAll("_", " ")}
                  <input value={value} onChange={(event) => setMapping((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" />
                </label>
              ))}
            </div>
            <button type="submit" disabled={saving} className="mt-4 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-300">
              {saving ? "Saving…" : "Save mappings"}
            </button>
          </form>

          <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">QuickBooks foundation</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{settings?.quickbooks_capabilities.notes ?? "Loading QuickBooks capability status…"}</p>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              <li>CSV export path: production-ready</li>
              <li>Export-ready formatting: available</li>
              <li>OAuth token storage: not configured</li>
              <li>Bidirectional sync engine: not implemented</li>
            </ul>
          </aside>
        </section>
      </div>
    </div>
  );
}
