"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type CreatedBroker = { id?: string };

type ApiResponse<T> = { data?: T };

function normalizeText(value: string): string {
  return value.trim();
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeOptionalInt(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;

  const parsed = Number.parseInt(normalized, 10);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return parsed;
}

export default function NewBrokerPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [mcNumber, setMcNumber] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [paymentTermsDays, setPaymentTermsDays] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canSubmit = useMemo(
    () => name.trim().length > 0 && !isSubmitting,
    [name, isSubmitting]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      return;
    }

    if (!name.trim()) {
      setErrorMessage("Broker name is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);

      const payload = {
        organization_id: organizationId,
        name: normalizeText(name),
        mc_number: normalizeOptionalText(mcNumber),
        email: normalizeOptionalText(email),
        phone: normalizeOptionalText(phone),
        payment_terms_days: normalizeOptionalInt(paymentTermsDays),
        notes: normalizeOptionalText(notes),
      };

      const response = await apiClient.post<ApiResponse<CreatedBroker>>("/brokers", payload, {
        token,
        organizationId,
      });

      const brokerId = response?.data?.id?.trim();
      router.push(brokerId ? `/dashboard/brokers/${brokerId}` : "/dashboard/brokers");
    } catch (caught: unknown) {
      setErrorMessage(caught instanceof Error ? caught.message : "Unable to create broker.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Brokers / New</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Create Broker</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Add a broker profile for consistent load handoff, contact, and payment follow-up operations.
            </p>
          </div>
          <Link href="/dashboard/brokers" className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
            Back to Brokers
          </Link>
        </div>

        {errorMessage ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Broker Name <span className="text-rose-600">*</span></label>
                <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Acme Freight Brokerage" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">MC Number</label>
                <input value={mcNumber} onChange={(event) => setMcNumber(event.target.value)} placeholder="MC123456" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Email</label>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="ops@broker.com" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Phone</label>
                <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="(555) 123-4567" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Payment Terms (days)</label>
                <input type="number" min={0} value={paymentTermsDays} onChange={(event) => setPaymentTermsDays(event.target.value)} placeholder="30" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-800">Notes</label>
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={5} placeholder="Preferred submission channel, invoice instructions, contact escalation notes..." className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </div>

            <div className="flex items-center gap-3">
              <button type="submit" disabled={!canSubmit} className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50">
                {isSubmitting ? "Creating..." : "Create Broker"}
              </button>
              <Link href="/dashboard/brokers" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
                Cancel
              </Link>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
