"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

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

type CreatedCustomerAccount = {
  id: string;
  account_name?: string | null;
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

export default function NewCustomerPage() {
  const router = useRouter();
  const organizationId = getOrganizationId() ?? "";

  const [accountName, setAccountName] = useState("");
  const [accountCode, setAccountCode] = useState("");
  const [primaryContactName, setPrimaryContactName] = useState("");
  const [primaryContactEmail, setPrimaryContactEmail] = useState("");
  const [primaryContactPhone, setPrimaryContactPhone] = useState("");
  const [billingEmail, setBillingEmail] = useState("");
  const [notes, setNotes] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return (
      organizationId.trim().length > 0 &&
      accountName.trim().length > 0 &&
      !isSubmitting &&
      isValidEmail(primaryContactEmail) &&
      isValidEmail(billingEmail)
    );
  }, [organizationId, accountName, isSubmitting, primaryContactEmail, billingEmail]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId.trim()) {
      setSubmitError("Organization context is missing. Please sign in again.");
      return;
    }

    if (!accountName.trim()) {
      setSubmitError("Account name is required.");
      return;
    }

    if (primaryContactEmail.trim() && !isValidEmail(primaryContactEmail)) {
      setSubmitError("Please enter a valid primary contact email.");
      return;
    }

    if (billingEmail.trim() && !isValidEmail(billingEmail)) {
      setSubmitError("Please enter a valid billing email.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const token = getAccessToken();

      const payload = {
        organization_id: organizationId.trim(),
        account_name: normalizeText(accountName),
        account_code: normalizeOptionalText(accountCode),
        primary_contact_name: normalizeOptionalText(primaryContactName),
        primary_contact_email: normalizeOptionalText(primaryContactEmail),
        primary_contact_phone: normalizeOptionalText(primaryContactPhone),
        billing_email: normalizeOptionalText(billingEmail),
        notes: normalizeOptionalText(notes),
      };

      const response = await apiClient.post<ApiResponse<CreatedCustomerAccount>>(
        "/customer-accounts",
        payload,
        {
          token: token ?? undefined,
          organizationId: organizationId.trim(),
        }
      );

      const createdCustomerId = response.data?.id;

      if (createdCustomerId && createdCustomerId.trim().length > 0) {
        router.push(`/dashboard/customers/${createdCustomerId}`);
        return;
      }

      router.push("/dashboard/customers");
    } catch (caught: unknown) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Failed to create customer account. Please verify the details and try again.";

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
              Dashboard / Customers / New
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Create New Customer Account
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Add a customer account so loads, billing, onboarding, and support workflows
              can be managed centrally.
            </p>
          </div>

          <Link
            href="/dashboard/customers"
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to Customers
          </Link>
        </div>

        {submitError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {submitError}
          </div>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label
                  htmlFor="account_name"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Account Name <span className="text-rose-600">*</span>
                </label>
                <input
                  id="account_name"
                  name="account_name"
                  type="text"
                  value={accountName}
                  onChange={(event) => setAccountName(event.target.value)}
                  placeholder="Acme Logistics"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="account_code"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Account Code
                </label>
                <input
                  id="account_code"
                  name="account_code"
                  type="text"
                  value={accountCode}
                  onChange={(event) => setAccountCode(event.target.value)}
                  placeholder="ACME-001"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="primary_contact_name"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Primary Contact Name
                </label>
                <input
                  id="primary_contact_name"
                  name="primary_contact_name"
                  type="text"
                  value={primaryContactName}
                  onChange={(event) => setPrimaryContactName(event.target.value)}
                  placeholder="Jane Smith"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="primary_contact_email"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Primary Contact Email
                </label>
                <input
                  id="primary_contact_email"
                  name="primary_contact_email"
                  type="email"
                  value={primaryContactEmail}
                  onChange={(event) => setPrimaryContactEmail(event.target.value)}
                  placeholder="jane@acmelogistics.com"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="primary_contact_phone"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Primary Contact Phone
                </label>
                <input
                  id="primary_contact_phone"
                  name="primary_contact_phone"
                  type="text"
                  value={primaryContactPhone}
                  onChange={(event) => setPrimaryContactPhone(event.target.value)}
                  placeholder="(555) 123-4567"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label
                  htmlFor="billing_email"
                  className="mb-2 block text-sm font-semibold text-slate-800"
                >
                  Billing Email
                </label>
                <input
                  id="billing_email"
                  name="billing_email"
                  type="email"
                  value={billingEmail}
                  onChange={(event) => setBillingEmail(event.target.value)}
                  placeholder="billing@acmelogistics.com"
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
                placeholder="Add any operational, onboarding, or billing notes for this account..."
                className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Organization Context</div>
                <div className="mt-1">
                  {organizationId
                    ? `Using active organization: ${organizationId}`
                    : "No organization context found. Please sign in again before creating a customer account."}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <div className="font-semibold text-slate-800">Initial Account State</div>
                <div className="mt-1">
                  Newly created customer accounts will use the backend default status.
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Create Customer Account"}
              </button>

              <Link
                href="/dashboard/customers"
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