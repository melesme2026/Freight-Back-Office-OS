"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { useDrivers } from "@/hooks/useDrivers";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type ApiResponse<T> = { data: T };

type CreatedLoad = { id: string };

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

type BrokerOption = {
  id: string;
  name: string;
  email?: string | null;
  mc_number?: string | null;
};

function parseAmount(value: string): string | null {
  const parsed = Number.parseFloat(value.trim());
  return Number.isFinite(parsed) ? parsed.toFixed(2) : null;
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
  const normalized = value.trim();
  return !normalized || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized);
}

export default function NewLoadPage() {
  const router = useRouter();

  const { customerAccounts, isLoading: isLoadingCustomers, error: customerAccountsError } = useCustomerAccounts();
  const { drivers, isLoading: isLoadingDrivers, error: driversError } = useDrivers();

  const organizationId = getOrganizationId() ?? "";

  const [customerAccountId, setCustomerAccountId] = useState("");
  const [driverId, setDriverId] = useState("");
  const [brokerId, setBrokerId] = useState("");
  const [brokerSearch, setBrokerSearch] = useState("");

  const [loadNumber, setLoadNumber] = useState("");
  const [pickupLocation, setPickupLocation] = useState("");
  const [deliveryLocation, setDeliveryLocation] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [brokerName, setBrokerName] = useState("");
  const [brokerEmail, setBrokerEmail] = useState("");
  const [currencyCode, setCurrencyCode] = useState("USD");
  const [notes, setNotes] = useState("");

  const [brokers, setBrokers] = useState<BrokerOption[]>([]);
  const [isLoadingBrokers, setIsLoadingBrokers] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const typedCustomerAccounts = (customerAccounts ?? []) as CustomerAccountOption[];
  const typedDrivers = (drivers ?? []) as DriverOption[];

  const effectiveCustomerAccounts = useMemo(() => {
    const active = typedCustomerAccounts.filter((account) => account.status.trim().toLowerCase() === "active");
    return active.length > 0 ? active : typedCustomerAccounts;
  }, [typedCustomerAccounts]);

  const effectiveDrivers = useMemo(() => {
    const active = typedDrivers.filter((driver) => driver.is_active);
    return active.length > 0 ? active : typedDrivers;
  }, [typedDrivers]);

  const filteredBrokers = useMemo(() => {
    const query = brokerSearch.trim().toLowerCase();
    if (!query) return brokers;
    return brokers.filter((broker) => [broker.name, broker.email, broker.mc_number].some((value) => value?.toLowerCase().includes(query)));
  }, [brokerSearch, brokers]);

  const selectedBroker = useMemo(() => brokers.find((broker) => broker.id === brokerId) ?? null, [brokers, brokerId]);

  const parsedAmount = useMemo(() => parseAmount(grossAmount), [grossAmount]);

  const canSubmit = useMemo(
    () =>
      organizationId.trim().length > 0 &&
      customerAccountId.trim().length > 0 &&
      driverId.trim().length > 0 &&
      loadNumber.trim().length > 0 &&
      (brokerId.trim().length > 0 || brokerName.trim().length > 0 || brokerEmail.trim().length > 0) &&
      !isSubmitting &&
      !isLoadingCustomers &&
      !isLoadingDrivers &&
      isValidEmail(brokerEmail),
    [organizationId, customerAccountId, driverId, loadNumber, brokerId, brokerName, brokerEmail, isSubmitting, isLoadingCustomers, isLoadingDrivers]
  );

  useEffect(() => {
    const token = getAccessToken();
    if (!organizationId) return;

    let mounted = true;

    async function loadBrokers() {
      try {
        setIsLoadingBrokers(true);
        const response = await apiClient.get<{ data?: Array<Record<string, unknown>> }>("/brokers?page=1&page_size=200", {
          token: token ?? undefined,
          organizationId,
        });

        if (!mounted) return;

        const normalized = (response.data ?? [])
          .map((item) => {
            const id = typeof item.id === "string" ? item.id : null;
            const name = typeof item.name === "string" ? item.name : null;
            if (!id || !name) return null;
            return {
              id,
              name,
              email: typeof item.email === "string" ? item.email : null,
              mc_number: typeof item.mc_number === "string" ? item.mc_number : null,
            } as BrokerOption;
          })
          .filter((item): item is BrokerOption => item !== null);

        setBrokers(normalized);
      } catch {
        if (mounted) setBrokers([]);
      } finally {
        if (mounted) setIsLoadingBrokers(false);
      }
    }

    void loadBrokers();

    return () => {
      mounted = false;
    };
  }, [organizationId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }
    const nextErrors: Record<string, string> = {};
    if (!customerAccountId.trim()) nextErrors.customer_account_id = "Customer account is required.";
    if (!driverId.trim()) nextErrors.driver_id = "Driver is required.";
    if (!loadNumber.trim()) nextErrors.load_number = "Load number is required.";
    if (!brokerId.trim() && !brokerName.trim() && !brokerEmail.trim()) {
      nextErrors.broker = "Broker selection or broker contact is required.";
    }
    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      setSubmitError("Please correct the highlighted fields.");
      return;
    }
    setFieldErrors({});

    if (grossAmount.trim() && parsedAmount === null) {
      setSubmitError("Gross amount must be a valid number.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const token = getAccessToken();

      const response = await apiClient.post<ApiResponse<CreatedLoad>>(
        "/loads",
        {
          organization_id: organizationId.trim(),
          customer_account_id: customerAccountId.trim(),
          driver_id: driverId.trim(),
          broker_id: normalizeOptionalText(brokerId),
          source_channel: "manual",
          load_number: loadNumber.trim(),
          pickup_location: normalizeOptionalText(pickupLocation),
          delivery_location: normalizeOptionalText(deliveryLocation),
          gross_amount: parsedAmount,
          broker_name_raw: normalizeOptionalText(brokerName),
          broker_email_raw: normalizeOptionalText(brokerEmail),
          currency_code: normalizeCurrencyCode(currencyCode),
          notes: normalizeOptionalText(notes),
        },
        {
          token: token ?? undefined,
          organizationId: organizationId.trim(),
        }
      );

      const createdLoadId = response.data?.id;
      router.push(createdLoadId ? `/dashboard/loads/${createdLoadId}` : "/dashboard/loads");
    } catch (caught: unknown) {
      setSubmitError(caught instanceof Error ? caught.message : "Failed to create load.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const pageError = submitError ?? customerAccountsError ?? driversError ?? null;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / New</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Create New Load</h1>
          </div>
          <Link href="/dashboard/loads" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">Back to Loads</Link>
        </div>

        {pageError ? <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{pageError}</div> : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Customer Account *</label>
                <select value={customerAccountId} onChange={(event) => setCustomerAccountId(event.target.value)} disabled={isLoadingCustomers} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm">
                  <option value="">{isLoadingCustomers ? "Loading customer accounts..." : "Select customer account"}</option>
                  {effectiveCustomerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>{account.account_name}{account.account_code ? ` (${account.account_code})` : ""}</option>
                  ))}
                </select>
                {fieldErrors.customer_account_id ? <p className="mt-1 text-xs text-rose-700">{fieldErrors.customer_account_id}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Driver *</label>
                <select value={driverId} onChange={(event) => setDriverId(event.target.value)} disabled={isLoadingDrivers} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm">
                  <option value="">{isLoadingDrivers ? "Loading drivers..." : "Select driver"}</option>
                  {effectiveDrivers.map((driver) => (
                    <option key={driver.id} value={driver.id}>{driver.full_name}{driver.phone ? ` • ${driver.phone}` : ""}</option>
                  ))}
                </select>
                {fieldErrors.driver_id ? <p className="mt-1 text-xs text-rose-700">{fieldErrors.driver_id}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Load Number *</label>
                <input type="text" value={loadNumber} onChange={(event) => setLoadNumber(event.target.value)} placeholder="LD-100245" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
                {fieldErrors.load_number ? <p className="mt-1 text-xs text-rose-700">{fieldErrors.load_number}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Gross Amount</label>
                <input type="number" step="0.01" min="0" value={grossAmount} onChange={(event) => setGrossAmount(event.target.value)} placeholder="2500.00" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Broker Lookup</label>
                <input type="text" value={brokerSearch} onChange={(event) => setBrokerSearch(event.target.value)} placeholder="Search broker name, email, MC..." className="mb-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
                <select value={brokerId} onChange={(event) => {
                  const value = event.target.value;
                  setBrokerId(value);
                  const selected = brokers.find((broker) => broker.id === value);
                  if (selected) {
                    setBrokerName(selected.name);
                    setBrokerEmail(selected.email ?? "");
                  }
                }} disabled={isLoadingBrokers} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm">
                  <option value="">{isLoadingBrokers ? "Loading brokers..." : "Select existing broker (recommended)"}</option>
                  {filteredBrokers.map((broker) => (
                    <option key={broker.id} value={broker.id}>{broker.name}{broker.email ? ` • ${broker.email}` : ""}{broker.mc_number ? ` • MC ${broker.mc_number}` : ""}</option>
                  ))}
                </select>
                <Link href="/dashboard/brokers" className="mt-2 inline-flex text-xs font-semibold text-brand-700 hover:text-brand-800">
                  Manage broker profiles →
                </Link>
                <p className="mt-1 text-xs text-slate-500">You can select a saved broker or enter broker email/name manually.</p>
                {fieldErrors.broker ? <p className="mt-1 text-xs text-rose-700">{fieldErrors.broker}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Broker Email</label>
                <input type="email" value={brokerEmail} onChange={(event) => setBrokerEmail(event.target.value)} placeholder="broker@example.com" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Pickup Location</label>
                <input type="text" value={pickupLocation} onChange={(event) => setPickupLocation(event.target.value)} placeholder="Chicago, IL" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Delivery Location</label>
                <input type="text" value={deliveryLocation} onChange={(event) => setDeliveryLocation(event.target.value)} placeholder="Atlanta, GA" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Broker Name (override)</label>
                <input type="text" value={brokerName} onChange={(event) => setBrokerName(event.target.value)} placeholder="Autofilled from selected broker" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-800">Currency Code</label>
                <input type="text" maxLength={3} value={currencyCode} onChange={(event) => setCurrencyCode(event.target.value.toUpperCase())} placeholder="USD" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm uppercase" />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-800">Notes</label>
              <textarea rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add operational notes..." className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <div className="font-semibold text-slate-800">Selected Broker</div>
              <div className="mt-1">{selectedBroker ? selectedBroker.name : "No broker selected"}</div>
              {selectedBroker?.email ? <div className="mt-1 text-xs text-slate-500">Email: {selectedBroker.email}</div> : null}
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="submit" disabled={!canSubmit} className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50">{isSubmitting ? "Creating..." : "Create Load"}</button>
              <Link href="/dashboard/loads" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">Cancel</Link>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
