"use client";

import { FormEvent, useState } from "react";

import { useCustomerAccounts } from "@/hooks/useCustomerAccounts";
import { useDrivers } from "@/hooks/useDrivers";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export default function DriverUploadsPage() {
  const { customerAccounts, isLoading: isCustomerLoading, error: customerError } = useCustomerAccounts();
  const { drivers } = useDrivers();

  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [selectedDriverId, setSelectedDriverId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId || !selectedCustomerId || !file) {
      setErrorMessage("Select a customer account and file before uploading.");
      return;
    }

    const formData = new FormData();
    formData.append("organization_id", organizationId);
    formData.append("customer_account_id", selectedCustomerId);
    formData.append("source_channel", "driver_portal");
    formData.append("file", file);
    if (selectedDriverId) {
      formData.append("driver_id", selectedDriverId);
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      await apiClient.post("/documents/upload", formData, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      });

      setSuccessMessage("Document uploaded successfully.");
      setFile(null);
      const uploadInput = event.currentTarget.elements.namedItem("upload-file") as HTMLInputElement | null;
      if (uploadInput) {
        uploadInput.value = "";
      }
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Uploads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Upload Documents</h1>
          <p className="mt-2 text-sm text-slate-600">
            Uploads are wired to the live document upload endpoint.
          </p>
        </div>

        {customerError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {customerError}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        <form onSubmit={(event) => void handleSubmit(event)} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="grid gap-5">
            <div>
              <label htmlFor="upload-customer" className="text-sm font-semibold text-slate-700">
                Customer account
              </label>
              <select
                id="upload-customer"
                value={selectedCustomerId}
                onChange={(event) => setSelectedCustomerId(event.target.value)}
                disabled={isCustomerLoading || customerAccounts.length === 0}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Select customer account</option>
                {customerAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.account_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="upload-driver" className="text-sm font-semibold text-slate-700">
                Driver (optional)
              </label>
              <select
                id="upload-driver"
                value={selectedDriverId}
                onChange={(event) => setSelectedDriverId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">No driver selected</option>
                {drivers.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    {driver.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="upload-file" className="text-sm font-semibold text-slate-700">
                Document file
              </label>
              <input
                id="upload-file"
                name="upload-file"
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex w-fit rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Uploading..." : "Upload document"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
