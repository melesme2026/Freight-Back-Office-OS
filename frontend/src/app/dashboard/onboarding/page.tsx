"use client";

import type { Route } from "next";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type OnboardingChecklist = {
  id: string;
  customer_account_id: string;
  status: string;
  documents_received: boolean;
  pricing_confirmed: boolean;
  payment_method_added: boolean;
  driver_profiles_created: boolean;
  channel_connected: boolean;
  go_live_ready: boolean;
  completed_at: string | null;
  updated_at: string | null;
};

type PilotReadinessItem = {
  label: string;
  done: boolean;
  href: Route;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function asBoolean(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "number") {
    return value === 1;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    return normalized === "true" || normalized === "1" || normalized === "yes";
  }

  return false;
}

function normalizeChecklist(payload: unknown): OnboardingChecklist | null {
  const root = asRecord(payload);
  const source = asRecord(root?.data) ?? root;

  if (!source) {
    return null;
  }

  const id = asString(source.id);
  const customerAccountId = asString(source.customer_account_id);

  if (!id || !customerAccountId) {
    return null;
  }

  return {
    id,
    customer_account_id: customerAccountId,
    status: asString(source.status) ?? "not_started",
    documents_received: asBoolean(source.documents_received),
    pricing_confirmed: asBoolean(source.pricing_confirmed),
    payment_method_added: asBoolean(source.payment_method_added),
    driver_profiles_created: asBoolean(source.driver_profiles_created),
    channel_connected: asBoolean(source.channel_connected),
    go_live_ready: asBoolean(source.go_live_ready),
    completed_at: asString(source.completed_at),
    updated_at: asString(source.updated_at),
  };
}

function isNotFoundError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("(404)");
}

function checklistQuery(customerAccountId: string, checklist: OnboardingChecklist): string {
  const params = new URLSearchParams({
    organization_id: getOrganizationId() ?? "",
    status: checklist.status,
    documents_received: String(checklist.documents_received),
    pricing_confirmed: String(checklist.pricing_confirmed),
    payment_method_added: String(checklist.payment_method_added),
    driver_profiles_created: String(checklist.driver_profiles_created),
    channel_connected: String(checklist.channel_connected),
    go_live_ready: String(checklist.go_live_ready),
  });

  if (checklist.completed_at) {
    params.set("completed_at", checklist.completed_at);
  }

  return `/onboarding/${encodeURIComponent(customerAccountId)}?${params.toString()}`;
}

export default function OnboardingPage() {
  const { customerAccounts, isLoading: isCustomerLoading, error: customerError } = useCustomerAccounts();

  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("");
  const [checklist, setChecklist] = useState<OnboardingChecklist | null>(null);
  const [isChecklistLoading, setIsChecklistLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const availableCustomerIds = useMemo(
    () => new Set(customerAccounts.map((account) => account.id)),
    [customerAccounts]
  );

  useEffect(() => {
    if (customerAccounts.length === 0) {
      if (selectedCustomerId) {
        setSelectedCustomerId("");
      }
      return;
    }

    if (!selectedCustomerId || !availableCustomerIds.has(selectedCustomerId)) {
      setSelectedCustomerId(customerAccounts[0].id);
    }
  }, [availableCustomerIds, customerAccounts, selectedCustomerId]);

  const selectedCustomer = useMemo(
    () => customerAccounts.find((account) => account.id === selectedCustomerId) ?? null,
    [customerAccounts, selectedCustomerId]
  );

  const loadChecklist = useCallback(async (): Promise<void> => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const isSelectedCustomerInScope = availableCustomerIds.has(selectedCustomerId);

    if (!selectedCustomerId || !organizationId || !isSelectedCustomerInScope) {
      setChecklist(null);
      return;
    }

    try {
      setIsChecklistLoading(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const payload = await apiClient.get<unknown>(
        `/onboarding/${encodeURIComponent(selectedCustomerId)}?organization_id=${encodeURIComponent(organizationId)}`,
        {
          token: token ?? undefined,
          organizationId,
        }
      );

      setChecklist(normalizeChecklist(payload));
    } catch (error: unknown) {
      if (isNotFoundError(error)) {
        setChecklist(null);
        return;
      }

      setChecklist(null);
      setErrorMessage(error instanceof Error ? error.message : "Failed to load onboarding checklist.");
    } finally {
      setIsChecklistLoading(false);
    }
  }, [availableCustomerIds, selectedCustomerId]);

  useEffect(() => {
    void loadChecklist();
  }, [loadChecklist]);

  async function initializeChecklist(): Promise<void> {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const isSelectedCustomerInScope = availableCustomerIds.has(selectedCustomerId);

    if (!selectedCustomerId || !organizationId || !isSelectedCustomerInScope) {
      setErrorMessage("Select a valid customer account from your organization to continue.");
      return;
    }

    try {
      setIsSaving(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const payload = await apiClient.post<unknown>(
        `/onboarding/${encodeURIComponent(selectedCustomerId)}/initialize?organization_id=${encodeURIComponent(organizationId)}`,
        undefined,
        {
          token: token ?? undefined,
          organizationId,
        }
      );

      const normalized = normalizeChecklist(payload);
      setChecklist(normalized);
      setSuccessMessage("Checklist initialized. You can now complete and save onboarding fields.");
      await loadChecklist();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to initialize onboarding checklist.");
    } finally {
      setIsSaving(false);
    }
  }

  async function saveChecklist(): Promise<void> {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    const isSelectedCustomerInScope = availableCustomerIds.has(selectedCustomerId);

    if (!checklist || !selectedCustomerId || !organizationId || !isSelectedCustomerInScope) {
      setErrorMessage("Checklist is not ready to save.");
      return;
    }

    try {
      setIsSaving(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const payload = await apiClient.put<unknown>(
        checklistQuery(selectedCustomerId, checklist),
        undefined,
        {
          token: token ?? undefined,
          organizationId,
        }
      );

      const normalized = normalizeChecklist(payload);
      setChecklist(normalized);
      setSuccessMessage("Checklist updated successfully.");
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to save onboarding checklist.");
    } finally {
      setIsSaving(false);
    }
  }

  function updateChecklistField(field: keyof OnboardingChecklist, value: string | boolean): void {
    setChecklist((current) => {
      if (!current) {
        return current;
      }

      return {
        ...current,
        [field]: value,
      };
    });
    setSuccessMessage(null);
  }

  const checklistItems: Array<{ key: keyof OnboardingChecklist; label: string }> = [
    { key: "documents_received", label: "Documents received" },
    { key: "pricing_confirmed", label: "Pricing confirmed" },
    { key: "payment_method_added", label: "Payment method added" },
    { key: "driver_profiles_created", label: "Driver profiles created" },
    { key: "channel_connected", label: "Channel connected" },
    { key: "go_live_ready", label: "Go-live ready" },
  ];

  const pilotReadinessItems = useMemo<PilotReadinessItem[]>(() => {
    const documentsReady = Boolean(checklist?.documents_received);
    const pricingReady = Boolean(checklist?.pricing_confirmed);
    const paymentReady = Boolean(checklist?.payment_method_added);
    const driverReady = Boolean(checklist?.driver_profiles_created);
    const channelReady = Boolean(checklist?.channel_connected);
    const goLiveReady = Boolean(checklist?.go_live_ready);

    return [
      { label: "Complete carrier profile", done: pricingReady || goLiveReady, href: "/dashboard/settings" as Route },
      { label: "Add driver", done: driverReady, href: "/dashboard/drivers/new" as Route },
      { label: "Add broker/customer", done: channelReady, href: "/dashboard/brokers/new" as Route },
      { label: "Create first load", done: goLiveReady || channelReady, href: "/dashboard/loads/new" as Route },
      { label: "Upload docs", done: documentsReady, href: "/dashboard/documents" as Route },
      { label: "Generate invoice", done: paymentReady || goLiveReady, href: "/dashboard/billing/invoices" as Route },
      { label: "Create packet", done: goLiveReady, href: "/dashboard/loads" as Route },
      { label: "Send packet", done: goLiveReady, href: "/dashboard/loads" as Route },
      { label: "Track payment", done: goLiveReady || paymentReady, href: "/dashboard/money" as Route },
    ];
  }, [checklist]);

  const pilotProgress = useMemo(() => {
    const completed = pilotReadinessItems.filter((item) => item.done).length;
    return Math.round((completed / pilotReadinessItems.length) * 100);
  }, [pilotReadinessItems]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Onboarding</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Onboarding Checklist</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Set up the carrier operation step-by-step before running your first live billing workflow.
          </p>
        </div>
        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
          <h2 className="text-base font-semibold text-slate-950">Who is who in this workflow</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            <li><span className="font-semibold">Carrier</span> = your trucking business that hauls the load and gets paid.</li>
            <li><span className="font-semibold">Driver</span> = the person hauling and uploading BOL/POD/supporting documents.</li>
            <li><span className="font-semibold">Broker</span> = the company/contact that receives the invoice packet and pays.</li>
          </ul>
          <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-slate-700">
            <p className="font-semibold text-slate-900">First test workflow</p>
            <p className="mt-1">
              Carrier profile → driver → broker → load → documents → invoice → submission packet → payment → dashboard visibility.
            </p>
          </div>
        </section>

        {customerError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {customerError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <label htmlFor="customer-account" className="text-sm font-semibold text-slate-700">
            Customer account
          </label>
          <select
            id="customer-account"
            value={selectedCustomerId}
            onChange={(event) => setSelectedCustomerId(event.target.value)}
            disabled={isCustomerLoading || customerAccounts.length === 0}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
          >
            {customerAccounts.length === 0 ? (
              <option value="">No customer accounts available</option>
            ) : null}
            {customerAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.account_name}
              </option>
            ))}
          </select>
        </section>

        {!isCustomerLoading && customerAccounts.length === 0 ? (
          <section className="mt-6 rounded-2xl border border-slate-200 bg-white px-6 py-8 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">No customer accounts yet</h2>
            <p className="mt-2 text-sm text-slate-600">
              Create a customer account first before initializing onboarding.
            </p>
            <Link
              href="/dashboard/customers/new"
              className="mt-4 inline-flex rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              Create Customer Account
            </Link>
          </section>
        ) : null}

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        {isChecklistLoading ? (
          <section className="mt-6 rounded-2xl border border-slate-200 bg-white px-6 py-8 text-sm text-slate-600 shadow-soft">
            Loading onboarding checklist...
          </section>
        ) : null}

        {!isChecklistLoading && selectedCustomer && !checklist ? (
          <section className="mt-6 rounded-2xl border border-slate-200 bg-white px-6 py-8 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">Checklist not initialized</h2>
            <p className="mt-2 text-sm text-slate-600">
              No onboarding checklist exists yet for {selectedCustomer.account_name}.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              This is expected on first run before initialization.
            </p>
            <button
              type="button"
              onClick={() => void initializeChecklist()}
              disabled={isSaving}
              className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? "Initializing..." : "Initialize Checklist"}
            </button>
          </section>
        ) : null}

        {!isChecklistLoading && checklist ? (
          <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-6 rounded-2xl border border-brand-200 bg-brand-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-950">Pilot onboarding progress</h2>
                <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-brand-700">
                  {pilotProgress}% complete
                </span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-brand-100">
                <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${pilotProgress}%` }} />
              </div>
              <ul className="mt-4 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                {pilotReadinessItems.map((item) => (
                  <li key={item.label} className="flex items-center justify-between gap-3 rounded-lg border border-white/70 bg-white px-3 py-2">
                    <span className={item.done ? "text-emerald-700" : "text-slate-700"}>
                      {item.done ? "✓ " : "○ "}
                      {item.label}
                    </span>
                    <Link href={item.href} className="text-xs font-semibold text-brand-700 hover:text-brand-800">
                      Open →
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label className="text-sm font-semibold text-slate-700" htmlFor="onboarding-status">
                  Status
                </label>
                <select
                  id="onboarding-status"
                  value={checklist.status}
                  onChange={(event) => updateChecklistField("status", event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                >
                  <option value="not_started">Not started</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-slate-700" htmlFor="completed-at">
                  Completed at (optional ISO timestamp)
                </label>
                <input
                  id="completed-at"
                  type="text"
                  value={checklist.completed_at ?? ""}
                  onChange={(event) => updateChecklistField("completed_at", event.target.value)}
                  placeholder="2026-04-12T15:30:00Z"
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {checklistItems.map((item) => (
                <label
                  key={item.key}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(checklist[item.key])}
                    onChange={(event) => updateChecklistField(item.key, event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void saveChecklist()}
                disabled={isSaving}
                className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? "Saving..." : "Save checklist"}
              </button>
              <button
                type="button"
                onClick={() => void loadChecklist()}
                disabled={isChecklistLoading || isSaving}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Refresh
              </button>
              <span className="text-xs text-slate-500">
                Last updated: {checklist.updated_at ?? "—"}
              </span>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
