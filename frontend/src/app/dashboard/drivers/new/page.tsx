"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type ApiError = {
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
};

type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
  error?: ApiError | null;
};

type CreatedDriver = {
  id: string;
  full_name?: string | null;
};

type CustomerAccountOption = {
  id: string;
  account_name: string;
  account_code?: string | null;
  status: string;
};

function normalizeText(value: string): string {
  return value.trim();
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function isValidEmail(value: string): boolean {
  const normalized = value.trim();

  if (!normalized) {
    return true;
  }

  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized);
}

function getStatusLabel(value: string | null | undefined): string {
  const normalized = value?.trim();
  return normalized && normalized.length > 0 ? normalized : "Unknown";
}

export default function NewDriverPage() {
  const router = useRouter();
  const organizationId = getOrganizationId() ?? "";

  const {
    customerAccounts,
    isLoading: isLoadingCustomers,
    error: customerAccountsError,
  } = useCustomerAccounts();

  const typedCustomerAccounts = (customerAccounts ?? []) as CustomerAccountOption[];

  const activeCustomerAccounts = useMemo(() => {
    return typedCustomerAccounts.filter(
      (account) => account.status.trim().toLowerCase() === "active"
    );
  }, [typedCustomerAccounts]);

  const effectiveCustomerAccounts =
    activeCustomerAccounts.length > 0 ? activeCustomerAccounts : typedCustomerAccounts;

  const [customerAccountId, setCustomerAccountId] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reactivationDriverId, setReactivationDriverId] = useState<string | null>(null);
  const [isReactivating, setIsReactivating] = useState(false);

  const selectedCustomerAccount = useMemo(() => {
    return (
      effectiveCustomerAccounts.find((account) => account.id === customerAccountId) ?? null
    );
  }, [effectiveCustomerAccounts, customerAccountId]);

  const canSubmit = useMemo(() => {
    return (
      organizationId.trim().length > 0 &&
      fullName.trim().length > 0 &&
      phone.trim().length > 0 &&
      !isSubmitting &&
      !isLoadingCustomers &&
      isValidEmail(email)
    );
  }, [organizationId, fullName, phone, isSubmitting, isLoadingCustomers, email]);

  const pageError = submitError ?? customerAccountsError ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }

    if (!fullName.trim()) {
      setSubmitError("Driver name is required.");
      return;
    }

    if (!phone.trim()) {
      setSubmitError("Driver phone is required.");
      return;
    }

    if (email.trim() && !isValidEmail(email)) {
      setSubmitError("Please enter a valid email address.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);
      setReactivationDriverId(null);

      const token = getAccessToken();

      const payload = {
        organization_id: organizationId.trim(),
        customer_account_id: normalizeOptionalText(customerAccountId),
        full_name: normalizeText(fullName),
        phone: normalizeText(phone),
        email: normalizeOptionalText(email),
        is_active: isActive,
      };

      const response = await apiClient.post<ApiResponse<CreatedDriver>>("/drivers", payload, {
        token: token ?? undefined,
        organizationId: organizationId.trim(),
      });

      const createdDriverId = response.data?.id;

      if (createdDriverId && createdDriverId.trim().length > 0) {
        router.push(`/dashboard/drivers/${createdDriverId}`);
        return;
      }

      router.push("/dashboard/drivers");
    } catch (caught: unknown) {
      if (caught instanceof ApiClientError) {
        if (caught.code === "driver_reactivation_required") {
          const driverIdFromError =
            typeof caught.details?.driver_id === "string"
              ? caught.details.driver_id.trim()
              : "";
          if (driverIdFromError) {
            setReactivationDriverId(driverIdFromError);
          }
        }
        setSubmitError(caught.message || "Failed to create driver.");
      } else {
        const message =
          caught instanceof Error
            ? caught.message
            : "Failed to create driver. Please verify the data and try again.";
        setSubmitError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function reactivateExistingDriver() {
    if (!reactivationDriverId) {
      return;
    }
    const token = getAccessToken();
    if (!token || !organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }
    try {
      setIsReactivating(true);
      await apiClient.patch(`/drivers/${encodeURIComponent(reactivationDriverId)}/reactivate`, undefined, {
        token,
        organizationId: organizationId.trim(),
      });
      router.push(`/dashboard/drivers/${reactivationDriverId}`);
    } catch (caught) {
      setSubmitError(caught instanceof Error ? caught.message : "Unable to reactivate driver.");
    } finally {
      setIsReactivating(false);
    }
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers / New
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Create New Driver
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Add a driver so loads, documents, and operational workflows can be linked
              correctly across the system.
            </p>
          </div>

          <Link
            href="/dashboard/drivers"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to Drivers
          </Link>
        </div>

        {pageError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {pageError}
            {reactivationDriverId ? (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={() => void reactivateExistingDriver()}
                  disabled={isReactivating}
                  className="rounded-lg bg-rose-700 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-60"
                >
                  {isReactivating ? "Reactivating..." : "Reactivate Existing Driver"}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label
                  htmlFor="full_name"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Driver Full Name <span className="text-rose-600">*</span>
                </label>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="John Doe"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="phone"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Phone <span className="text-rose-600">*</span>
                </label>
                <input
                  id="phone"
                  name="phone"
                  type="text"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  placeholder="(555) 123-4567"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="driver@example.com"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="customer_account_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Customer Account
                </label>
                <select
                  id="customer_account_id"
                  name="customer_account_id"
                  value={customerAccountId}
                  onChange={(event) => setCustomerAccountId(event.target.value)}
                  disabled={isLoadingCustomers}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-slate-100"
                >
                  <option value="">
                    {isLoadingCustomers
                      ? "Loading customer accounts..."
                      : "Optional: select customer account"}
                  </option>
                  {effectiveCustomerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_name}
                      {account.account_code ? ` (${account.account_code})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(event) => setIsActive(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                <span>
                  <span className="block text-sm font-semibold text-slate-800">
                    Active driver
                  </span>
                  <span className="mt-1 block text-sm text-slate-600">
                    Keep this enabled for drivers that should appear in active operational
                    workflows and selection lists.
                  </span>
                </span>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Organization Context</div>
                <div className="mt-1">
                  {organizationId
                    ? `Using active organization: ${organizationId}`
                    : "No organization context found. Please sign in again before creating a driver."}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Selected Customer</div>
                <div className="mt-1">
                  {selectedCustomerAccount
                    ? `${selectedCustomerAccount.account_name}${
                        selectedCustomerAccount.account_code
                          ? ` (${selectedCustomerAccount.account_code})`
                          : ""
                      }`
                    : "No customer linked yet."}
                </div>
                {selectedCustomerAccount ? (
                  <div className="mt-1 text-xs text-slate-500">
                    Status: {getStatusLabel(selectedCustomerAccount.status)}
                  </div>
                ) : null}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Driver State</div>
                <div className="mt-1">{isActive ? "Active" : "Inactive"}</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Create Driver"}
              </button>

              <Link
                href="/dashboard/drivers"
                className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Cancel
              </Link>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
