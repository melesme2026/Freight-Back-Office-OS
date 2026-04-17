"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { useDrivers } from "@/hooks/useDrivers";
import { useLoads } from "@/hooks/useLoads";
import { apiClient } from "@/lib/api-client";
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

type CreatedSupportTicket = {
  id: string;
  subject?: string | null;
  status?: string | null;
  priority?: string | null;
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
  email?: string | null;
  is_active: boolean;
};

type LoadOption = {
  id: string;
  load_number: string;
  status: string;
  customer_account_id?: string | null;
  driver_id?: string | null;
};

type StaffUserOption = {
  id: string;
  full_name: string;
  email: string;
  role: string | null;
  is_active: boolean;
};

type TicketPriority = "low" | "normal" | "high" | "urgent";

const PRIORITY_OPTIONS: Array<{ value: TicketPriority; label: string }> = [
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

function normalizeText(value: string): string {
  return value.trim();
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function getStatusLabel(value: string | null | undefined): string {
  const normalized = value?.trim();
  return normalized && normalized.length > 0 ? normalized : "Unknown";
}

export default function NewSupportTicketPage() {
  const router = useRouter();
  const organizationId = getOrganizationId() ?? "";

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

  const {
    loads,
    isLoading: isLoadingLoads,
    error: loadsError,
  } = useLoads();

  const typedCustomerAccounts = (customerAccounts ?? []) as CustomerAccountOption[];
  const typedDrivers = (drivers ?? []) as DriverOption[];
  const typedLoads = (loads ?? []) as LoadOption[];
  const [staffUsers, setStaffUsers] = useState<StaffUserOption[]>([]);
  const [staffUsersError, setStaffUsersError] = useState<string | null>(null);
  const [isLoadingStaffUsers, setIsLoadingStaffUsers] = useState<boolean>(true);

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("normal");
  const [customerAccountId, setCustomerAccountId] = useState("");
  const [driverId, setDriverId] = useState("");
  const [loadId, setLoadId] = useState("");
  const [assignedToStaffUserId, setAssignedToStaffUserId] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadStaffUsers() {
      const token = getAccessToken();

      if (!organizationId.trim()) {
        if (isMounted) {
          setStaffUsers([]);
          setStaffUsersError("Organization context is missing.");
          setIsLoadingStaffUsers(false);
        }
        return;
      }

      try {
        setIsLoadingStaffUsers(true);
        setStaffUsersError(null);

        const response = await apiClient.get<ApiResponse<unknown>>(
          "/staff-users?page=1&page_size=200&is_active=true",
          {
            token: token ?? undefined,
            organizationId: organizationId.trim(),
          }
        );

        const items = Array.isArray(response.data) ? response.data : [];
        const normalized = items
          .map((item) => {
            if (!item || typeof item !== "object" || Array.isArray(item)) {
              return null;
            }

            const record = item as Record<string, unknown>;
            const id = typeof record.id === "string" ? record.id.trim() : "";
            const fullName =
              typeof record.full_name === "string" ? record.full_name.trim() : "";
            const email = typeof record.email === "string" ? record.email.trim() : "";
            const isActive = record.is_active !== false;

            if (!id || !fullName || !email) {
              return null;
            }

            return {
              id,
              full_name: fullName,
              email,
              role:
                typeof record.role === "string" && record.role.trim().length > 0
                  ? record.role.trim()
                  : null,
              is_active: isActive,
            } satisfies StaffUserOption;
          })
          .filter((item) => item !== null) as StaffUserOption[];

        if (isMounted) {
          setStaffUsers(normalized);
        }
      } catch (error) {
        if (isMounted) {
          setStaffUsers([]);
          setStaffUsersError(
            error instanceof Error ? error.message : "Failed to load staff users."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingStaffUsers(false);
        }
      }
    }

    void loadStaffUsers();

    return () => {
      isMounted = false;
    };
  }, [organizationId]);

  const activeCustomerAccounts = useMemo(() => {
    return typedCustomerAccounts.filter(
      (account) => account.status.trim().toLowerCase() === "active"
    );
  }, [typedCustomerAccounts]);

  const activeDrivers = useMemo(() => {
    return typedDrivers.filter((driver) => driver.is_active);
  }, [typedDrivers]);

  const activeLoads = useMemo(() => {
    return typedLoads.filter((load) => load.status.trim().toLowerCase() !== "archived");
  }, [typedLoads]);

  const effectiveCustomerAccounts =
    activeCustomerAccounts.length > 0 ? activeCustomerAccounts : typedCustomerAccounts;

  const effectiveDrivers =
    activeDrivers.length > 0 ? activeDrivers : typedDrivers;

  const effectiveLoads = activeLoads.length > 0 ? activeLoads : typedLoads;

  const selectedCustomerAccount = useMemo(() => {
    return effectiveCustomerAccounts.find((account) => account.id === customerAccountId) ?? null;
  }, [effectiveCustomerAccounts, customerAccountId]);

  const selectedDriver = useMemo(() => {
    return effectiveDrivers.find((driver) => driver.id === driverId) ?? null;
  }, [effectiveDrivers, driverId]);

  const selectedLoad = useMemo(() => {
    return effectiveLoads.find((load) => load.id === loadId) ?? null;
  }, [effectiveLoads, loadId]);

  const activeStaffUsers = useMemo(() => {
    return staffUsers.filter((staffUser) => staffUser.is_active);
  }, [staffUsers]);

  const selectedAssignee = useMemo(() => {
    return activeStaffUsers.find((staffUser) => staffUser.id === assignedToStaffUserId) ?? null;
  }, [activeStaffUsers, assignedToStaffUserId]);

  const pageError =
    submitError ??
    customerAccountsError ??
    driversError ??
    loadsError ??
    staffUsersError ??
    null;

  const canSubmit = useMemo(() => {
    return (
      organizationId.trim().length > 0 &&
      subject.trim().length > 0 &&
      description.trim().length > 0 &&
      !isSubmitting &&
      !isLoadingCustomers &&
      !isLoadingDrivers &&
      !isLoadingLoads &&
      !isLoadingStaffUsers
    );
  }, [
    organizationId,
    subject,
    description,
    isSubmitting,
    isLoadingCustomers,
    isLoadingDrivers,
    isLoadingLoads,
    isLoadingStaffUsers,
  ]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }

    if (!subject.trim()) {
      setSubmitError("Subject is required.");
      return;
    }

    if (!description.trim()) {
      setSubmitError("Description is required.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const token = getAccessToken();

      const payload = {
        organization_id: organizationId.trim(),
        subject: normalizeText(subject),
        description: normalizeText(description),
        customer_account_id: normalizeOptionalText(customerAccountId),
        driver_id: normalizeOptionalText(driverId),
        load_id: normalizeOptionalText(loadId),
        priority,
        assigned_to_staff_user_id: normalizeOptionalText(assignedToStaffUserId),
      };

      const response = await apiClient.post<ApiResponse<CreatedSupportTicket>>(
        "/support/tickets",
        payload,
        {
          token: token ?? undefined,
          organizationId: organizationId.trim(),
        }
      );

      const createdTicketId = response.data?.id;

      if (createdTicketId && createdTicketId.trim().length > 0) {
        router.push("/dashboard/support");
        return;
      }

      router.push("/dashboard/support");
    } catch (caught: unknown) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Failed to create support ticket. Please verify the details and try again.";

      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Support / New
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Create Support Ticket
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Open an operational, customer, billing, or load-related support ticket
              using the live backend support workflow.
            </p>
          </div>

          <Link
            href="/dashboard/support"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to Support
          </Link>
        </div>

        {pageError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {pageError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="mb-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h2 className="text-sm font-semibold text-slate-900">Operations templates</h2>
            <p className="mt-1 text-xs text-slate-600">
              Use these built-in templates for broker/AP follow-up during support escalations.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <a href="/business-assets/invoice-template.md" target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 bg-white px-3 py-1 font-semibold text-slate-700 hover:bg-slate-100">
                Invoice template
              </a>
              <a href="/business-assets/invoice-email-template.txt" target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 bg-white px-3 py-1 font-semibold text-slate-700 hover:bg-slate-100">
                Invoice email template
              </a>
              <a href="/business-assets/invoice-followup-template.txt" target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 bg-white px-3 py-1 font-semibold text-slate-700 hover:bg-slate-100">
                Payment follow-up template
              </a>
            </div>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="md:col-span-2">
                <label
                  htmlFor="subject"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Subject <span className="text-rose-600">*</span>
                </label>
                <input
                  id="subject"
                  name="subject"
                  type="text"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  placeholder="Missing invoice upload for active load"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="priority"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Priority
                </label>
                <select
                  id="priority"
                  name="priority"
                  value={priority}
                  onChange={(event) => setPriority(event.target.value as TicketPriority)}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                >
                  {PRIORITY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="assigned_to_staff_user_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Assign to staff
                </label>
                <select
                  id="assigned_to_staff_user_id"
                  name="assigned_to_staff_user_id"
                  value={assignedToStaffUserId}
                  onChange={(event) => setAssignedToStaffUserId(event.target.value)}
                  disabled={isLoadingStaffUsers}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-slate-100"
                >
                  <option value="">
                    {isLoadingStaffUsers ? "Loading staff users..." : "Optional: auto-route"}
                  </option>
                  {activeStaffUsers.map((staffUser) => (
                    <option key={staffUser.id} value={staffUser.id}>
                      {staffUser.full_name} • {staffUser.email}
                    </option>
                  ))}
                </select>
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

              <div>
                <label
                  htmlFor="driver_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Driver
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
                    {isLoadingDrivers ? "Loading drivers..." : "Optional: select driver"}
                  </option>
                  {effectiveDrivers.map((driver) => (
                    <option key={driver.id} value={driver.id}>
                      {driver.full_name}
                      {driver.phone ? ` • ${driver.phone}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label
                  htmlFor="load_id"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Load
                </label>
                <select
                  id="load_id"
                  name="load_id"
                  value={loadId}
                  onChange={(event) => setLoadId(event.target.value)}
                  disabled={isLoadingLoads}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200 disabled:cursor-not-allowed disabled:bg-slate-100"
                >
                  <option value="">
                    {isLoadingLoads ? "Loading loads..." : "Optional: select load"}
                  </option>
                  {effectiveLoads.map((load) => (
                    <option key={load.id} value={load.id}>
                      {load.load_number || load.id} • {getStatusLabel(load.status)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label
                htmlFor="description"
                className="mb-2 block text-sm font-semibold text-slate-800"
              >
                Description <span className="text-rose-600">*</span>
              </label>
              <textarea
                id="description"
                name="description"
                rows={7}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe the issue, expected behavior, current blocker, and any relevant load, billing, or customer context..."
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-5">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Organization</div>
                <div className="mt-1 break-all">
                  {organizationId || "Missing organization context"}
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
                    : "None"}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Selected Driver</div>
                <div className="mt-1">
                  {selectedDriver ? selectedDriver.full_name : "None"}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Selected Load</div>
                <div className="mt-1">
                  {selectedLoad ? selectedLoad.load_number || selectedLoad.id : "None"}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Assigned Staff</div>
                <div className="mt-1">
                  {selectedAssignee
                    ? `${selectedAssignee.full_name} (${selectedAssignee.email})`
                    : "Auto-route"}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Create Support Ticket"}
              </button>

              <Link
                href="/dashboard/support"
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
