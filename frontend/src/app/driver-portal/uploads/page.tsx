"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { useLoads } from "@/hooks/useLoads";
import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { labelForDocumentType } from "@/lib/driver-portal";

type DriverDocument = {
  id: string;
  load_id: string | null;
  load_number: string | null;
  document_type: string | null;
  original_filename: string | null;
  processing_status: string | null;
  received_at: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asText(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

function normalizeDocuments(payload: unknown): DriverDocument[] {
  const root = asRecord(payload);
  const items = Array.isArray(root?.data) ? root.data : Array.isArray(payload) ? payload : [];

  return items
    .map((item) => {
      const record = asRecord(item);
      const id = asText(record?.id);
      if (!record || !id) return null;

      return {
        id,
        load_id: asText(record.load_id),
        load_number: asText(record.load_number),
        document_type: asText(record.document_type),
        original_filename: asText(record.original_filename) ?? asText(record.file_name),
        processing_status: asText(record.processing_status),
        received_at: asText(record.received_at) ?? asText(record.created_at),
      };
    })
    .filter((item): item is DriverDocument => item !== null);
}

function formatDateTime(value: string | null): string {
  if (!value) return "Submitted just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getFriendlyError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 409) {
      return error.message || "A document already exists for that load. Open the load to replace it.";
    }
    if (error.status === 403 || error.status === 401) {
      return "You do not have access to upload that document. Sign in again or contact dispatch.";
    }
  }
  return error instanceof Error ? error.message : "Upload failed. Please try again.";
}

export default function DriverUploadsPage() {
  const { loads, isLoading: isLoadingLoads } = useLoads({ scope: "driver" });

  const [selectedLoadId, setSelectedLoadId] = useState("");
  const [documentType, setDocumentType] = useState("proof_of_delivery");
  const [file, setFile] = useState<File | null>(null);
  const [documents, setDocuments] = useState<DriverDocument[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const MAX_UPLOAD_MB = 15;
  const acceptedTypes = "PDF, JPG, PNG, WEBP, HEIC, HEIF, TIFF";

  const loadOptions = useMemo(() => {
    return loads.map((load) => ({
      id: load.id,
      label: load.load_number || load.id,
    }));
  }, [loads]);

  async function fetchDocuments() {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    if (!organizationId) {
      setDocuments([]);
      setIsLoadingDocuments(false);
      return;
    }

    try {
      setIsLoadingDocuments(true);
      const payload = await apiClient.get<unknown>("/documents?page=1&page_size=100", {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      });
      setDocuments(normalizeDocuments(payload));
    } catch {
      setDocuments([]);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  useEffect(() => {
    void fetchDocuments();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) return;

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId || !file || !documentType.trim()) {
      setErrorMessage("Select a document type and file before uploading.");
      return;
    }

    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setErrorMessage(`File is too large. Upload a file under ${MAX_UPLOAD_MB}MB.`);
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

      const response = await apiClient.post<unknown>("/driver/documents/upload", formData, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      });

      const uploadedDocument = normalizeDocuments(response)[0] ?? normalizeDocuments({ data: [asRecord(response)?.data] })[0];
      if (uploadedDocument) {
        setDocuments((current) => [uploadedDocument, ...current.filter((item) => item.id !== uploadedDocument.id)]);
      }

      setSuccessMessage(`Upload successful: ${file.name} (${labelForDocumentType(documentType.trim())}).`);
      setFile(null);
      setSelectedLoadId("");
      const uploadInput = event.currentTarget.elements.namedItem("upload-file") as HTMLInputElement | null;
      if (uploadInput) {
        uploadInput.value = "";
      }
      await fetchDocuments();
    } catch (error: unknown) {
      setErrorMessage(getFriendlyError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  const documentsByLoad = useMemo(() => {
    const names = new Map(loadOptions.map((load) => [load.id, load.label]));
    const grouped = new Map<string, { label: string; documents: DriverDocument[] }>();

    for (const document of documents) {
      const key = document.load_id ?? "unassigned";
      const label = document.load_number ?? (document.load_id ? names.get(document.load_id) : null) ?? "Not linked to a load";
      const existing = grouped.get(key) ?? { label, documents: [] };
      existing.documents.push(document);
      grouped.set(key, existing);
    }

    return Array.from(grouped.entries()).map(([id, value]) => ({ id, ...value }));
  }, [documents, loadOptions]);

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Uploads</p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Upload Documents</h1>
          <p className="mt-2 text-sm text-slate-600">
            Upload PODs, BOLs, rate confirmations, and photos from your phone. Link the file to a load when possible so dispatch can review it faster.
          </p>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
            <p className="font-semibold text-slate-900">Mobile upload tips</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4">
              <li>Select the assigned load and document type.</li>
              <li>Take a photo or choose a PDF/image from your phone.</li>
              <li>Wait for the green success confirmation before leaving this page.</li>
            </ol>
            <p className="mt-3 text-xs text-slate-600">
              Accepted file types: {acceptedTypes}. Maximum file size: {MAX_UPLOAD_MB}MB.
            </p>
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        <form onSubmit={(event) => void handleSubmit(event)} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
          <div className="grid gap-5">
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">What is usually missing?</p>
              <ul className="mt-1 list-disc pl-5 text-xs">
                <li>After pickup: upload Bill of Lading.</li>
                <li>After delivery: upload POD / delivery receipt.</li>
                <li>If extra charges: upload lumper, scale, or accessorial proof.</li>
              </ul>
            </div>
            <div>
              <label htmlFor="upload-document-type" className="text-sm font-semibold text-slate-700">
                Document type
              </label>
              <select
                id="upload-document-type"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
                disabled={isSubmitting}
                className="touch-target mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-base disabled:bg-slate-100 sm:text-sm"
              >
                <option value="proof_of_delivery">Proof of Delivery</option>
                <option value="bill_of_lading">Bill of Lading</option>
                <option value="rate_confirmation">Rate Confirmation</option>
                <option value="invoice">Invoice</option>
                <option value="lumper_receipt">Lumper Receipt</option>
                <option value="detention_support">Detention Support</option>
                <option value="scale_ticket">Scale Ticket</option>
                <option value="accessorial_support">Accessorial Support</option>
                <option value="damage_claim_photo">Damage Claim Photo</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label htmlFor="upload-load" className="text-sm font-semibold text-slate-700">
                Assigned load
              </label>
              <select
                id="upload-load"
                value={selectedLoadId}
                onChange={(event) => setSelectedLoadId(event.target.value)}
                disabled={isSubmitting || isLoadingLoads}
                className="touch-target mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-base disabled:bg-slate-100 sm:text-sm"
              >
                <option value="">Select a load (recommended)</option>
                {loadOptions.map((load) => (
                  <option key={load.id} value={load.id}>
                    {load.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">
                Only loads assigned to your driver account are available here.
              </p>
            </div>

            <div>
              <label htmlFor="upload-file" className="text-sm font-semibold text-slate-700">
                File or photo
              </label>
              <input
                id="upload-file"
                name="upload-file"
                type="file"
                accept="image/*,application/pdf"
                capture="environment"
                disabled={isSubmitting}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="mt-2 w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-700 file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-brand-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white disabled:cursor-not-allowed disabled:opacity-60"
              />
              {file ? (
                <p className="mt-2 break-all text-xs text-slate-600">
                  Selected: {file.name} ({(file.size / (1024 * 1024)).toFixed(2)}MB)
                </p>
              ) : null}
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !file}
              className="touch-target min-h-12 rounded-xl bg-brand-600 px-5 py-3 text-base font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300 sm:text-sm"
            >
              {isSubmitting ? "Uploading document..." : "Upload Document"}
            </button>
          </div>
        </form>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Upload history</h2>
              <p className="mt-1 text-sm text-slate-600">Documents submitted from your assigned loads appear here after upload.</p>
            </div>
            <Link href="/driver-portal/loads" className="touch-target inline-flex items-center rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">
              View loads
            </Link>
          </div>

          {isLoadingDocuments ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">Loading upload history...</div>
          ) : documentsByLoad.length === 0 ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">No documents submitted yet.</div>
          ) : (
            <div className="mt-4 space-y-4">
              {documentsByLoad.map((group) => (
                <div key={group.id} className="rounded-xl border border-slate-200 p-3">
                  <div className="font-semibold text-slate-900">{group.label}</div>
                  <div className="mt-3 space-y-2">
                    {group.documents.map((document) => (
                      <div key={document.id} className="flex flex-col gap-2 rounded-lg bg-slate-50 px-3 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <div className="font-medium text-slate-900">{labelForDocumentType(document.document_type ?? "other")}</div>
                          <div className="break-all text-xs text-slate-600">{document.original_filename ?? "Uploaded document"}</div>
                        </div>
                        <div className="text-xs text-slate-500 sm:text-right">
                          <div className="font-semibold capitalize text-emerald-700">{document.processing_status ?? "submitted"}</div>
                          <div>{formatDateTime(document.received_at)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
