"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type BrokerDetail = {
  id: string;
  name: string;
  mc_number?: string | null;
  email?: string | null;
  phone?: string | null;
  payment_terms_days?: number | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function normalizeBroker(payload: unknown, brokerId: string): BrokerDetail | null {
  const root = asRecord(payload);
  const source = asRecord(root?.data) ?? root;
  if (!source) return null;

  const id = asString(source.id) ?? brokerId;
  const name = asString(source.name);
  if (!name) return null;

  const termsValue = source.payment_terms_days;
  const paymentTerms =
    typeof termsValue === "number"
      ? termsValue
      : typeof termsValue === "string"
        ? Number.parseInt(termsValue, 10)
        : null;

  return {
    id,
    name,
    mc_number: asString(source.mc_number),
    email: asString(source.email),
    phone: asString(source.phone),
    payment_terms_days: Number.isFinite(paymentTerms as number) ? paymentTerms : null,
    notes: asString(source.notes),
    created_at: asString(source.created_at),
    updated_at: asString(source.updated_at),
  };
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeOptionalInteger(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = Number.parseInt(normalized, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function BrokerDetailPage() {
  const params = useParams();
  const router = useRouter();

  const brokerId = useMemo(() => {
    const raw = params?.brokerId;
    if (Array.isArray(raw)) return raw[0] ?? "";
    if (typeof raw === "string") return raw;
    return "";
  }, [params]);

  const [broker, setBroker] = useState<BrokerDetail | null>(null);
  const [name, setName] = useState("");
  const [mcNumber, setMcNumber] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [paymentTermsDays, setPaymentTermsDays] = useState("");
  const [notes, setNotes] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getAccessToken();
      const organizationId = getOrganizationId();

      if (!token || !organizationId || !brokerId) {
        setErrorMessage("Missing session context or broker id.");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setErrorMessage(null);

        const payload = await apiClient.get<unknown>(`/brokers/${encodeURIComponent(brokerId)}`, {
          token,
          organizationId,
        });

        const normalized = normalizeBroker(payload, brokerId);
        if (!normalized) {
          throw new Error("Broker details could not be parsed.");
        }

        setBroker(normalized);
        setName(normalized.name);
        setMcNumber(normalized.mc_number ?? "");
        setEmail(normalized.email ?? "");
        setPhone(normalized.phone ?? "");
        setPaymentTermsDays(
          normalized.payment_terms_days !== null && normalized.payment_terms_days !== undefined
            ? String(normalized.payment_terms_days)
            : ""
        );
        setNotes(normalized.notes ?? "");
      } catch (caught: unknown) {
        setErrorMessage(caught instanceof Error ? caught.message : "Unable to load broker.");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [brokerId]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId || !brokerId) {
      setErrorMessage("Missing session context or broker id.");
      return;
    }

    if (!name.trim()) {
      setErrorMessage("Broker name is required.");
      return;
    }

    try {
      setIsSaving(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const payload = await apiClient.patch<unknown>(
        `/brokers/${encodeURIComponent(brokerId)}`,
        {
          name: name.trim(),
          mc_number: normalizeOptionalText(mcNumber),
          email: normalizeOptionalText(email),
          phone: normalizeOptionalText(phone),
          payment_terms_days: normalizeOptionalInteger(paymentTermsDays),
          notes: normalizeOptionalText(notes),
        },
        { token, organizationId }
      );

      const normalized = normalizeBroker(payload, brokerId);
      if (!normalized) {
        throw new Error("Updated broker response could not be parsed.");
      }

      setBroker(normalized);
      setSuccessMessage("Broker profile updated.");
    } catch (caught: unknown) {
      setErrorMessage(caught instanceof Error ? caught.message : "Unable to save broker updates.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Brokers / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {isLoading ? "Loading broker..." : broker?.name ?? "Broker"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => router.push("/dashboard/loads/new")} className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
              Create Load
            </button>
            <Link href="/dashboard/brokers" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
              Back to Brokers
            </Link>
          </div>
        </div>

        {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {successMessage ? <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{successMessage}</div> : null}

        <div className="grid gap-6 lg:grid-cols-[1.5fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">Broker Profile</h2>
            <form className="mt-5 space-y-5" onSubmit={handleSave}>
              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-800">Broker Name <span className="text-rose-600">*</span></label>
                  <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-800">MC Number</label>
                  <input value={mcNumber} onChange={(event) => setMcNumber(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-800">Email</label>
                  <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-800">Phone</label>
                  <input value={phone} onChange={(event) => setPhone(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-800">Payment Terms (days)</label>
                  <input type="number" min={0} value={paymentTermsDays} onChange={(event) => setPaymentTermsDays(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Notes</label>
                <textarea rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" disabled={isLoading || isSaving} />
              </div>
              <button type="submit" disabled={isLoading || isSaving} className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50">
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </form>
          </section>

          <aside className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">Operational Metadata</h2>
              <dl className="mt-4 space-y-3 text-sm text-slate-700">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Broker ID</dt>
                  <dd className="mt-1 break-all">{broker?.id ?? brokerId ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Created</dt>
                  <dd className="mt-1">{formatDate(broker?.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Updated</dt>
                  <dd className="mt-1">{formatDate(broker?.updated_at)}</dd>
                </div>
              </dl>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
