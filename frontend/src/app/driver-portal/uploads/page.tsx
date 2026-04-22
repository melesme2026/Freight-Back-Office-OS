"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";

import { useLoads } from "@/hooks/useLoads";
import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export default function DriverUploadsPage() {
  const { loads, isLoading: isLoadingLoads } = useLoads();

  const [selectedLoadId, setSelectedLoadId] = useState("");
  const [documentType, setDocumentType] = useState("bol");
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadOptions = useMemo(() => {
    return loads.map((load) => ({
      id: load.id,
      label: load.load_number || load.id,
    }));
  }, [loads]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId || !file || !documentType.trim()) {
      setErrorMessage("Select a document type and file before uploading.");
      return;
    }

    const formData = new FormData();
    formData.append("organization_id", organizationId);
    formData.append("document_type", documentType.trim());
    formData.append("file", file);
    if (selectedLoadId) {
      formData.append("load_id", selectedLoadId);
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      await apiClient.post("/driver/documents/upload", formData, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      });

      setSuccessMessage("Document uploaded successfully.");
      setFile(null);
      setSelectedLoadId("");
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
            Upload rate confirmations, PODs, invoices, and supporting paperwork, then optionally link each file to a load.
          </p>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            <p className="font-semibold text-slate-900">How uploads work</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4">
              <li>Select document type and file (PDF or image).</li>
              <li>Optionally select a load to attach the file immediately.</li>
              <li>Submit and monitor processing from the staff Documents screen.</li>
            </ol>
          </div>
        </div>

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
              <label htmlFor="upload-document-type" className="text-sm font-semibold text-slate-700">
                Document type
              </label>
              <select
                id="upload-document-type"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="rate_confirmation">Rate Confirmation</option>
                <option value="proof_of_delivery">Proof of Delivery</option>
                <option value="bill_of_lading">Bill of Lading</option>
                <option value="invoice">Invoice</option>
                <option value="lumper_receipt">Lumper Receipt</option>
                <option value="detention_support">Detention Support</option>
                <option value="scale_ticket">Scale Ticket</option>
                <option value="accessorial_support">Accessorial Support</option>
                <option value="damage_claim_photo">Damage Claim Photo</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Driver is resolved automatically from your signed-in driver account.
            </div>

            <div>
              <label htmlFor="upload-load" className="text-sm font-semibold text-slate-700">
                Load (optional)
              </label>
              <select
                id="upload-load"
                value={selectedLoadId}
                onChange={(event) => setSelectedLoadId(event.target.value)}
                disabled={isLoadingLoads}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">No load selected</option>
                {loadOptions.map((load) => (
                  <option key={load.id} value={load.id}>
                    {load.label}
                  </option>
                ))}
              </select>
              {!isLoadingLoads && loadOptions.length === 0 ? (
                <p className="mt-2 text-xs text-amber-700">
                  No driver loads are available yet. You can still upload documents without linking,
                  then staff can attach them later.
                </p>
              ) : null}
            </div>

            <div>
              <label htmlFor="upload-file" className="text-sm font-semibold text-slate-700">
                Document file
              </label>
              <input
                id="upload-file"
                name="upload-file"
                type="file"
                accept="application/pdf,image/*"
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
            <Link
              href="/driver-portal/loads"
              className="inline-flex w-fit rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              View my loads
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
