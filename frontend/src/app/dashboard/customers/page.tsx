"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";

type CustomerAccountRow = {
  id: string;
  account_name: string | null;
  account_code: string | null;
  status: string | null;
  primary_contact_name: string | null;
  billing_email: string | null;
};

function badgeClass(status?: string) {
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

function badgeLabel(status?: string) {
  const normalized = status?.trim();
  return normalized && normalized.length > 0 ? normalized : "Unknown";
}

function normalizeText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeCustomerAccount(value: unknown): CustomerAccountRow | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const record = value as Record<string, unknown>;
  const id = normalizeText(record.id);

  if (!id) {
    return null;
  }

  return {
    id,
    account_name: normalizeText(record.account_name),
    account_code: normalizeText(record.account_code),
    status: normalizeText(record.status),
    primary_contact_name: normalizeText(record.primary_contact_name),
    billing_email: normalizeText(record.billing_email),
  };
}

export default function CustomersPage() {
  const router = useRouter();
  const { customerAccounts, isLoading, error, refetch } = useCustomerAccounts();

  const normalizedCustomers = useMemo<CustomerAccountRow[]>(() => {
    if (!Array.isArray(customerAccounts)) {
      return [];
    }

    return customerAccounts
      .map((customer) => normalizeCustomerAccount(customer))
      .filter((customer): customer is CustomerAccountRow => customer !== null);
  }, [customerAccounts]);

  const { totalCustomers, activeCustomers, prospectCustomers } = useMemo(() => {
    const total = normalizedCustomers.length;
    const active = normalizedCustomers.filter(
      (customer) => (customer.status ?? "").toLowerCase() === "active"
    ).length;
    const prospect = normalizedCustomers.filter(
      (customer) => (customer.status ?? "").toLowerCase() === "prospect"
    ).length;

    return {
      totalCustomers: total,
      activeCustomers: active,
      prospectCustomers: prospect,
    };
  }, [normalizedCustomers]);

  function openCustomerDetail(customerId: string) {
    router.push(`/dashboard/customers/${customerId}`);
  }

  function openNewCustomer() {
    router.push("/dashboard/customers/new");
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Customers</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Customers</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Manage freight customers, operational readiness, billing contacts, and account-level
              activity.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isLoading}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-soft transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>

            <button
              type="button"
              onClick={openNewCustomer}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              New Customer Account
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total accounts</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : totalCustomers}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Active accounts</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">
              {isLoading ? "..." : activeCustomers}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Prospects</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">
              {isLoading ? "..." : prospectCustomers}
            </div>
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-rose-800">
                  Unable to load customer accounts
                </h2>
                <p className="mt-1 text-sm text-rose-700">{error}</p>
              </div>

              <button
                type="button"
                onClick={() => void refetch()}
                className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Account</th>
                  <th className="px-5 py-4 font-semibold">Code</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Primary Contact</th>
                  <th className="px-5 py-4 font-semibold">Billing Email</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-10 text-center text-slate-500">
                      Loading customer accounts...
                    </td>
                  </tr>
                ) : normalizedCustomers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-10 text-center text-slate-600">
                      <div className="space-y-2">
                        <p className="font-semibold text-slate-700">No customer accounts yet.</p>
                        <p>Create a customer account so onboarding, billing, and payment tracking have the right account scope.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  normalizedCustomers.map((customer) => (
                    <tr key={customer.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900">
                          {customer.account_name ?? "Unnamed Account"}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">{customer.id}</div>
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {customer.account_code ?? "—"}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badgeClass(
                            customer.status ?? undefined
                          )}`}
                        >
                          {badgeLabel(customer.status ?? undefined)}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {customer.primary_contact_name ?? "—"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {customer.billing_email ?? "—"}
                      </td>

                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={() => openCustomerDetail(customer.id)}
                          className="text-sm font-semibold text-brand-700 transition hover:text-brand-800"
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
