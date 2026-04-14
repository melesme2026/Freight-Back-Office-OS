"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

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
  created_at?: string | null;
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

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asNullableString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function asCustomerAccountRecord(value: unknown): CustomerAccountRecord | null {
  const root = asRecord(value);
  if (!root) {
    return null;
  }

  const record = asRecord(root.data) ?? asRecord(root.customer_account) ?? asRecord(root.item) ?? root;
  const id = asNullableString(record.id);

  if (!id) {
    return null;
  }

  return {
    id,
    account_name: asNullableString(record.account_name),
    account_code: asNullableString(record.account_code),
    status: asNullableString(record.status),
    billing_email: asNullableString(record.billing_email),
    primary_contact_name: asNullableString(record.primary_contact_name),
    primary_contact_email: asNullableString(record.primary_contact_email),
    primary_contact_phone: asNullableString(record.primary_contact_phone),
    notes: asNullableString(record.notes),
    created_at: asNullableString(record.created_at),
    updated_at: asNullableString(record.updated_at),
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

  const [customer, setCustomer] = useState<CustomerAccountRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [editAccountName, setEditAccountName] = useState("");
  const [editAccountCode, setEditAccountCode] = useState("");
  const [editStatus, setEditStatus] = useState("prospect");
  const [editPrimaryContactName, setEditPrimaryContactName] = useState("");
  const [editPrimaryContactEmail, setEditPrimaryContactEmail] = useState("");
  const [editPrimaryContactPhone, setEditPrimaryContactPhone] = useState("");
  const [editBillingEmail, setEditBillingEmail] = useState("");
  const [editNotes, setEditNotes] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadCustomer() {
      if (!customerId) {
        if (isMounted) {
          setError("Invalid customer identifier.");
          setCustomer(null);
          setIsLoading(false);
        }
        return;
      }

      const token = getAccessToken();
      const organizationId = getOrganizationId();

      if (!token || !organizationId) {
        if (isMounted) {
          setError("Missing session context. Please sign in again.");
          setCustomer(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        const payload = await apiClient.get<unknown>(
          `/customer-accounts/${encodeURIComponent(customerId)}`,
          {
            token,
            organizationId,
          }
        );

        const normalized = asCustomerAccountRecord(payload);
        if (!normalized) {
          throw new Error("Customer response could not be normalized.");
        }

        if (isMounted) {
          setCustomer(normalized);
          setEditAccountName(normalized.account_name ?? "");
          setEditAccountCode(normalized.account_code ?? "");
          setEditStatus((normalized.status ?? "prospect").toLowerCase());
          setEditPrimaryContactName(normalized.primary_contact_name ?? "");
          setEditPrimaryContactEmail(normalized.primary_contact_email ?? "");
          setEditPrimaryContactPhone(normalized.primary_contact_phone ?? "");
          setEditBillingEmail(normalized.billing_email ?? "");
          setEditNotes(normalized.notes ?? "");
        }
      } catch (caught) {
        if (isMounted) {
          const message =
            caught instanceof Error
              ? caught.message
              : "An unexpected error occurred while loading the customer.";
          setError(message);
          setCustomer(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadCustomer();

    return () => {
      isMounted = false;
    };
  }, [customerId]);

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

  async function saveCustomerEdits() {
    if (!customer) {
      return;
    }

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setUpdateError("Missing session context. Please sign in again.");
      return;
    }

    if (!editAccountName.trim()) {
      setUpdateError("Account name is required.");
      return;
    }

    try {
      setIsSaving(true);
      setUpdateError(null);
      setUpdateMessage(null);

      const payload = await apiClient.patch<unknown>(
        `/customer-accounts/${encodeURIComponent(customer.id)}`,
        {
          account_name: editAccountName.trim(),
          account_code: editAccountCode.trim() ? editAccountCode.trim() : null,
          status: editStatus.trim() ? editStatus.trim().toLowerCase() : "prospect",
          primary_contact_name: editPrimaryContactName.trim() ? editPrimaryContactName.trim() : null,
          primary_contact_email: editPrimaryContactEmail.trim() ? editPrimaryContactEmail.trim() : null,
          primary_contact_phone: editPrimaryContactPhone.trim() ? editPrimaryContactPhone.trim() : null,
          billing_email: editBillingEmail.trim() ? editBillingEmail.trim() : null,
          notes: editNotes.trim() ? editNotes.trim() : null,
        },
        {
          token,
          organizationId,
        }
      );

      const normalized = asCustomerAccountRecord(payload);
      if (!normalized) {
        throw new Error("Updated customer response could not be normalized.");
      }

      setCustomer(normalized);
      setEditAccountName(normalized.account_name ?? "");
      setEditAccountCode(normalized.account_code ?? "");
      setEditStatus((normalized.status ?? "prospect").toLowerCase());
      setEditPrimaryContactName(normalized.primary_contact_name ?? "");
      setEditPrimaryContactEmail(normalized.primary_contact_email ?? "");
      setEditPrimaryContactPhone(normalized.primary_contact_phone ?? "");
      setEditBillingEmail(normalized.billing_email ?? "");
      setEditNotes(normalized.notes ?? "");
      setIsEditing(false);
      setUpdateMessage("Customer account updated.");
    } catch (caught: unknown) {
      setUpdateError(caught instanceof Error ? caught.message : "Unable to update customer account.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  if (!customerId) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
                onClick={() => router.refresh()}
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
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
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
              onClick={() => {
                setIsEditing((current) => !current);
                setUpdateError(null);
                setUpdateMessage(null);
                if (customer) {
                  setEditAccountName(customer.account_name ?? "");
                  setEditAccountCode(customer.account_code ?? "");
                  setEditStatus((customer.status ?? "prospect").toLowerCase());
                  setEditPrimaryContactName(customer.primary_contact_name ?? "");
                  setEditPrimaryContactEmail(customer.primary_contact_email ?? "");
                  setEditPrimaryContactPhone(customer.primary_contact_phone ?? "");
                  setEditBillingEmail(customer.billing_email ?? "");
                  setEditNotes(customer.notes ?? "");
                }
              }}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              {isEditing ? "Cancel Edit" : "Edit Account"}
            </button>
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
                    Created
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(customer.created_at)}
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

              {updateError ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {updateError}
                </div>
              ) : null}
              {updateMessage ? (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {updateMessage}
                </div>
              ) : null}

              {isEditing ? (
                <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <input
                      type="text"
                      value={editAccountName}
                      onChange={(event) => setEditAccountName(event.target.value)}
                      placeholder="Account name"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                    <input
                      type="text"
                      value={editAccountCode}
                      onChange={(event) => setEditAccountCode(event.target.value)}
                      placeholder="Account code"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <select
                      value={editStatus}
                      onChange={(event) => setEditStatus(event.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    >
                      <option value="prospect">Prospect</option>
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                    <input
                      type="email"
                      value={editBillingEmail}
                      onChange={(event) => setEditBillingEmail(event.target.value)}
                      placeholder="Billing email"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <input
                      type="text"
                      value={editPrimaryContactName}
                      onChange={(event) => setEditPrimaryContactName(event.target.value)}
                      placeholder="Primary contact name"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                    <input
                      type="email"
                      value={editPrimaryContactEmail}
                      onChange={(event) => setEditPrimaryContactEmail(event.target.value)}
                      placeholder="Primary contact email"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                    <input
                      type="text"
                      value={editPrimaryContactPhone}
                      onChange={(event) => setEditPrimaryContactPhone(event.target.value)}
                      placeholder="Primary contact phone"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                  </div>
                  <textarea
                    value={editNotes}
                    onChange={(event) => setEditNotes(event.target.value)}
                    rows={4}
                    placeholder="Notes"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                    disabled={isSaving}
                  />
                  <button
                    type="button"
                    onClick={() => void saveCustomerEdits()}
                    disabled={isSaving}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
                  >
                    {isSaving ? "Saving..." : "Save Account Changes"}
                  </button>
                </div>
              ) : null}
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
    </div>
  );
}
