"use client";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";

function statusBadgeClass(status?: string) {
  switch ((status ?? "").toLowerCase()) {
    case "active":
      return "bg-emerald-100 text-emerald-800";
    case "prospect":
      return "bg-amber-100 text-amber-800";
    case "inactive":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

type ReadinessItem = {
  label: string;
  value: boolean;
};

type CustomerAccountRecord = {
  id: string;
  account_name?: string | null;
  account_code?: string | null;
  status?: string | null;
  billing_email?: string | null;
  primary_contact_name?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  notes?: string | null;
  updated_at?: string | null;
};

function normalizeRouteParam(value: string | string[] | undefined): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (Array.isArray(value) && value.length > 0) {
    const first = value[0];
    if (typeof first === "string") {
      const trimmed = first.trim();
      return trimmed.length > 0 ? trimmed : null;
    }
  }

  return null;
}

function asCustomerAccountRecord(value: unknown): CustomerAccountRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = typeof record.id === "string" ? record.id.trim() : "";

  if (id.length === 0) {
    return null;
  }

  return {
    id,
    account_name:
      typeof record.account_name === "string" ? record.account_name.trim() : null,
    account_code:
      typeof record.account_code === "string" ? record.account_code.trim() : null,
    status: typeof record.status === "string" ? record.status.trim() : null,
    billing_email:
      typeof record.billing_email === "string" ? record.billing_email.trim() : null,
    primary_contact_name:
      typeof record.primary_contact_name === "string"
        ? record.primary_contact_name.trim()
        : null,
    primary_contact_email:
      typeof record.primary_contact_email === "string"
        ? record.primary_contact_email.trim()
        : null,
    primary_contact_phone:
      typeof record.primary_contact_phone === "string"
        ? record.primary_contact_phone.trim()
        : null,
    notes: typeof record.notes === "string" ? record.notes.trim() : null,
    updated_at:
      typeof record.updated_at === "string" ? record.updated_at.trim() : null,
  };
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

export default function CustomerDetailPage() {
  const router = useRouter();
  const params = useParams<{ customerId: string | string[] }>();
  const customerId = normalizeRouteParam(params?.customerId);

  const { customerAccounts, isLoading, error, refetch } = useCustomerAccounts();

  const normalizedCustomerAccounts = useMemo<CustomerAccountRecord[]>(() => {
    if (!Array.isArray(customerAccounts)) {
      return [];
    }

    return customerAccounts
      .map((item) => asCustomerAccountRecord(item))
      .filter((item): item is CustomerAccountRecord => item !== null);
  }, [customerAccounts]);

  const customer = useMemo(() => {
    if (!customerId) {
      return null;
    }

    return normalizedCustomerAccounts.find((item) => item.id === customerId) ?? null;
  }, [customerId, normalizedCustomerAccounts]);

  const readinessItems = useMemo<ReadinessItem[]>(() => {
    if (!customer) {
      return [];
    }

    return [
      {
        label: "Primary Contact Added",
        value: Boolean(customer.primary_contact_name?.trim()),
      },
      {
        label: "Billing Email Added",
        value: Boolean(customer.billing_email?.trim()),
      },
      {
        label: "Contact Email Added",
        value: Boolean(customer.primary_contact_email?.trim()),
      },
      {
        label: "Contact Phone Added",
        value: Boolean(customer.primary_contact_phone?.trim()),
      },
      {
        label: "Notes Added",
        value: Boolean(customer.notes?.trim()),
      },
      {
        label: "Account Active",
        value: (customer.status ?? "").toLowerCase() === "active",
      },
    ];
  }, [customer]);

  const accountDisplayName =
    customer?.account_name && customer.account_name.length > 0
      ? customer.account_name
      : customer?.id ?? "Customer Account";

  function goToCustomers() {
    router.push("/dashboard/customers");
  }

  function goToLoads() {
    router.push("/dashboard/loads");
  }

  function goToBilling() {
    router.push("/dashboard/billing");
  }

  function goToSupport() {
    router.push("/dashboard/support");
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Customers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Loading customer...
            </h1>
            <p className="mt-3 text-sm text-slate-600">
              Fetching customer account details.
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (!customerId) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Customers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">
              Invalid customer identifier
            </h1>
            <p className="mt-2 text-sm text-rose-700">
              The requested customer route did not include a valid customer ID.
            </p>

            <div className="mt-5">
              <button
                type="button"
                onClick={goToCustomers}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Customers
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Customers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">
              Unable to load customer
            </h1>
            <p className="mt-2 text-sm text-rose-700">{error}</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void refetch()}
                className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>

              <button
                type="button"
                onClick={goToCustomers}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Customers
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!customer) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Customers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Customer not found
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              No customer account matched ID:
            </p>
            <p className="mt-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-800">
              {customerId}
            </p>

            <div className="mt-5">
              <button
                type="button"
                onClick={goToCustomers}
                className="inline-flex rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Customers
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8">
          <button
            type="button"
            onClick={goToCustomers}
            className="text-sm font-medium text-brand-700 transition hover:text-brand-800"
          >
            ← Back to Customers
          </button>
        </div>

        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Customers / Detail
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {accountDisplayName}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Customer account detail including contacts, readiness signals, and
              V1 account metadata.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={goToBilling}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Open Billing
            </button>
            <button
              type="button"
              onClick={goToLoads}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              Open Loads
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">
                  Account Summary
                </h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(
                    customer.status ?? undefined
                  )}`}
                >
                  {customer.status && customer.status.length > 0
                    ? customer.status
                    : "unknown"}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Account Name
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.account_name ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Customer ID
                  </div>
                  <div className="mt-1 break-all text-sm font-medium text-slate-900">
                    {customer.id}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Account Code
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.account_code ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Billing Email
                  </div>
                  <div className="mt-1 break-all text-sm font-medium text-slate-900">
                    {customer.billing_email ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Primary Contact
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.primary_contact_name ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Contact Email
                  </div>
                  <div className="mt-1 break-all text-sm font-medium text-slate-900">
                    {customer.primary_contact_email ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Contact Phone
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.primary_contact_phone ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Last Updated
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(customer.updated_at)}
                  </div>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-500">
                  Notes
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {customer.notes && customer.notes.length > 0
                    ? customer.notes
                    : "No account notes have been added yet."}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-4 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">
                  Operational Follow-Up
                </h2>
                <button
                  type="button"
                  onClick={goToLoads}
                  className="text-sm font-semibold text-brand-700 transition hover:text-brand-800"
                >
                  Open Loads →
                </button>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-700">
                  Customer-specific recent load activity is not yet wired from a
                  dedicated backend relation endpoint. For V1, use the Loads
                  workspace to review active freight activity tied to this
                  account.
                </p>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={goToLoads}
                  className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  View Load Operations
                </button>
                <button
                  type="button"
                  onClick={goToBilling}
                  className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Billing Workspace
                </button>
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Account Readiness
              </h2>

              <div className="space-y-3">
                {readinessItems.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-slate-800">
                      {item.label}
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        item.value
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {item.value ? "Yes" : "No"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Quick Actions
              </h2>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={goToCustomers}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Back to Customers
                </button>
                <button
                  type="button"
                  onClick={goToBilling}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Billing
                </button>
                <button
                  type="button"
                  onClick={goToSupport}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Support
                </button>
                <button
                  type="button"
                  onClick={goToLoads}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Loads
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}