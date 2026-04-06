"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { useDrivers } from "@/hooks/useDrivers";

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

type CreatedLoad = {
  id: string;
  load_number?: string | null;
};

type CustomerAccountOption = {
  id: string;
  account_name: string;
  account_code?: string | null;
  status: string;
};

type DriverOption = {
  id: string;
  full_name: string;
  phone?: string | null;
  is_active: boolean;
};

function parseAmount(value: string): string | null {
  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  const parsed = Number.parseFloat(trimmed);
  return Number.isFinite(parsed) ? parsed.toFixed(2) : null;
}

function normalizeText(value: string): string {
  return value.trim();
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeCurrencyCode(value: string): string {
  const normalized = value.trim().toUpperCase();
  return normalized.length > 0 ? normalized : "USD";
}

function isValidEmail(value: string): boolean {
  if (!value.trim()) {
    return true;
  }

  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export default function NewLoadPage() {
  const router = useRouter();

  const {
    customerAccounts,
    isLoading: isLoadingCustomers,
    error: customerAccountsError,
  } = useCustomerAccounts();

  const {
    drivers,
    isLoading: isLoadingDrivers,
    error: driversError,
  } = useDrivers();

  const organizationId = getOrganizationId() ?? "";

  const [customerAccountId, setCustomerAccountId] = useState("");
  const [driverId, setDriverId] = useState("");
  const [brokerId, setBrokerId] = useState("");

  const [loadNumber, setLoadNumber] = useState("");
  const [pickupLocation, setPickupLocation] = useState("");
  const [deliveryLocation, setDeliveryLocation] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [brokerName, setBrokerName] = useState("");
  const [brokerEmail, setBrokerEmail] = useState("");
  const [currencyCode, setCurrencyCode] = useState("USD");
  const [notes, setNotes] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const typedCustomerAccounts = (customerAccounts ?? []) as CustomerAccountOption[];
  const typedDrivers = (drivers ?? []) as DriverOption[];

  const activeCustomerAccounts = useMemo(() => {
    return typedCustomerAccounts.filter(
      (account) => account.status.trim().toLowerCase() === "active"
    );
  }, [typedCustomerAccounts]);

  const activeDrivers = useMemo(() => {
    return typedDrivers.filter((driver) => driver.is_active);
  }, [typedDrivers]);

  const effectiveCustomerAccounts =
    activeCustomerAccounts.length > 0 ? activeCustomerAccounts : typedCustomerAccounts;

  const effectiveDrivers =
    activeDrivers.length > 0 ? activeDrivers : typedDrivers;

  const selectedCustomerAccount = useMemo(() => {
    return effectiveCustomerAccounts.find((account) => account.id === customerAccountId) ?? null;
  }, [effectiveCustomerAccounts, customerAccountId]);

  const selectedDriver = useMemo(() => {
    return effectiveDrivers.find((driver) => driver.id === driverId) ?? null;
  }, [effectiveDrivers, driverId]);

  const parsedAmount = useMemo(() => parseAmount(grossAmount), [grossAmount]);

  const canSubmit = useMemo(() => {
    return (
      organizationId.trim().length > 0 &&
      customerAccountId.trim().length > 0 &&
      driverId.trim().length > 0 &&
      loadNumber.trim().length > 0 &&
      !isSubmitting &&
      !isLoadingCustomers &&
      !isLoadingDrivers &&
      isValidEmail(brokerEmail)
    );
  }, [
    organizationId,
    customerAccountId,
    driverId,
    loadNumber,
    isSubmitting,
    isLoadingCustomers,
    isLoadingDrivers,
    brokerEmail,
  ]);

  const pageError = submitError ?? customerAccountsError ?? driversError ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }

    if (!customerAccountId.trim()) {
      setSubmitError("Please select a customer account.");
      return;
    }

    if (!driverId.trim()) {
      setSubmitError("Please select a driver.");
      return;
    }

    if (!loadNumber.trim()) {
      setSubmitError("Load number is required.");
      return;
    }

    if (brokerEmail.trim() && !isValidEmail(brokerEmail)) {
      setSubmitError("Please enter a valid broker email address.");
      return;
    }

    if (grossAmount.trim() && parsedAmount === null) {
      setSubmitError("Gross amount must be a valid number.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const token = getAccessToken();
      const query = new URLSearchParams();

      query.set("organization_id", organizationId.trim());
      query.set("customer_account_id", customerAccountId.trim());
      query.set("driver_id", driverId.trim());
      query.set("source_channel", "manual");
      query.set("load_number", normalizeText(loadNumber));

      const normalizedBrokerId = normalizeOptionalText(brokerId);
      if (normalizedBrokerId) {
        query.set("broker_id", normalizedBrokerId);
      }

      const normalizedPickupLocation = normalizeOptionalText(pickupLocation);
      if (normalizedPickupLocation) {
        query.set("pickup_location", normalizedPickupLocation);
      }

      const normalizedDeliveryLocation = normalizeOptionalText(deliveryLocation);
      if (normalizedDeliveryLocation) {
        query.set("delivery_location", normalizedDeliveryLocation);
      }

      if (parsedAmount) {
        query.set("gross_amount", parsedAmount);
      }

      const normalizedBrokerName = normalizeOptionalText(brokerName);
      if (normalizedBrokerName) {
        query.set("broker_name_raw", normalizedBrokerName);
      }

      const normalizedBrokerEmail = normalizeOptionalText(brokerEmail);
      if (normalizedBrokerEmail) {
        query.set("broker_email_raw", normalizedBrokerEmail);
      }

      query.set("currency_code", normalizeCurrencyCode(currencyCode));

      const normalizedNotes = normalizeOptionalText(notes);
      if (normalizedNotes) {
        query.set("notes", normalizedNotes);
      }

      const response = await apiClient.post<ApiResponse<CreatedLoad>>(
        `/loads?${query.toString()}`,
        undefined,
        {
          token: token ?? undefined,
          organizationId: organizationId.trim(),
        }
      );

      const createdLoadId = response.data?.id;

      if (createdLoadId && createdLoadId.trim().length > 0) {
        router.push(`/dashboard/loads/${createdLoadId}`);
        return;
      }

      router.push("/dashboard/loads");
    } catch (caught: unknown) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Failed to create load. Please verify the selected records and try again.";

      setSubmitError(message);
      setIsSubmitting(false);
      return;
    }

    setIsSubmitting(false);
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Loads / New
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Create New Load
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Add a freight load after booking so operations can track workflow,
              documents, and billing from one place.
            </p>
          </div>

          <Link
            href="/dashboard/loads"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to Loads
          </Link>
        </div>

        {pageError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {pageError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label
                  htmlFor="customer_account_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Customer Account <span className="text-rose-600">*</span>
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
                      : "Select customer account"}
                  </option>
                  {effectiveCustomerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_name}
                      {account.account_code ? ` (${account.account_code})` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="driver_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Driver <span className="text-rose-600">*</span>
                </label>
                <select
                  id="driver_id"
                  name="driver_id"
                  value={driverId}
                  onChange={(event) => setDriverId(event.target.value)}
                  disabled={isLoadingDrivers}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-slate-100"
                >
                  <option value="">
                    {isLoadingDrivers ? "Loading drivers..." : "Select driver"}
                  </option>
                  {effectiveDrivers.map((driver) => (
                    <option key={driver.id} value={driver.id}>
                      {driver.full_name}
                      {driver.phone ? ` • ${driver.phone}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="load_number"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Load Number <span className="text-rose-600">*</span>
                </label>
                <input
                  id="load_number"
                  name="load_number"
                  type="text"
                  value={loadNumber}
                  onChange={(event) => setLoadNumber(event.target.value)}
                  placeholder="LD-100245"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="gross_amount"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Gross Amount
                </label>
                <input
                  id="gross_amount"
                  name="gross_amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={grossAmount}
                  onChange={(event) => setGrossAmount(event.target.value)}
                  placeholder="2500.00"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="pickup_location"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Pickup Location
                </label>
                <input
                  id="pickup_location"
                  name="pickup_location"
                  type="text"
                  value={pickupLocation}
                  onChange={(event) => setPickupLocation(event.target.value)}
                  placeholder="Chicago, IL"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="delivery_location"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Delivery Location
                </label>
                <input
                  id="delivery_location"
                  name="delivery_location"
                  type="text"
                  value={deliveryLocation}
                  onChange={(event) => setDeliveryLocation(event.target.value)}
                  placeholder="Atlanta, GA"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="broker_name_raw"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Broker Name
                </label>
                <input
                  id="broker_name_raw"
                  name="broker_name_raw"
                  type="text"
                  value={brokerName}
                  onChange={(event) => setBrokerName(event.target.value)}
                  placeholder="TQL"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="broker_email_raw"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Broker Email
                </label>
                <input
                  id="broker_email_raw"
                  name="broker_email_raw"
                  type="email"
                  value={brokerEmail}
                  onChange={(event) => setBrokerEmail(event.target.value)}
                  placeholder="broker@example.com"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="currency_code"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Currency Code
                </label>
                <input
                  id="currency_code"
                  name="currency_code"
                  type="text"
                  maxLength={3}
                  value={currencyCode}
                  onChange={(event) =>
                    setCurrencyCode(event.target.value.toUpperCase())
                  }
                  placeholder="USD"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm uppercase text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="broker_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Broker ID
                </label>
                <input
                  id="broker_id"
                  name="broker_id"
                  type="text"
                  value={brokerId}
                  onChange={(event) => setBrokerId(event.target.value)}
                  placeholder="Optional broker UUID"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="notes"
                className="mb-2 block text-sm font-semibold text-slate-800"
              >
                Notes
              </label>
              <textarea
                id="notes"
                name="notes"
                rows={5}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Add any operational notes for this load..."
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Organization Context</div>
                <div className="mt-1">
                  {organizationId
                    ? `Using active organization: ${organizationId}`
                    : "No organization context found. Please sign in again before creating a load."}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Selected Customer</div>
                <div className="mt-1">
                  {selectedCustomerAccount
                    ? selectedCustomerAccount.account_name
                    : "No customer selected yet."}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Selected Driver</div>
                <div className="mt-1">
                  {selectedDriver
                    ? selectedDriver.full_name
                    : "No driver selected yet."}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Create Load"}
              </button>

              <Link
                href="/dashboard/loads"
                className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Cancel
              </Link>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}