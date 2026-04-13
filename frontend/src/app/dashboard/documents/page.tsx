"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

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

type LoadDocument = {
  id: string;
  organization_id: string;
  customer_account_id: string;
  driver_id?: string | null;
  load_id?: string | null;
  source_channel?: string | null;
  document_type?: string | null;
  original_filename?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  storage_bucket?: string | null;
  storage_key?: string | null;
  processing_status?: string | null;
  page_count?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  uploaded_by_staff_user_name?: string | null;
  uploaded_by_staff_user_id?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function asOptionalNumber(value: unknown): number | null | undefined {
  if (value === undefined) {
    return undefined;
  }

  if (value === null) {
    return null;
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
}

function normalizeDocument(value: unknown): LoadDocument | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const id = asString(record.id);
  const organizationId = asString(record.organization_id);
  const customerAccountId = asString(record.customer_account_id);

  if (!id || !organizationId || !customerAccountId) {
    return null;
  }

  return {
    id,
    organization_id: organizationId,
    customer_account_id: customerAccountId,
    driver_id: asString(record.driver_id),
    load_id: asString(record.load_id),
    source_channel: asString(record.source_channel),
    document_type: asString(record.document_type),
    original_filename: asString(record.original_filename),
    mime_type: asString(record.mime_type),
    file_size_bytes: asOptionalNumber(record.file_size_bytes),
    storage_bucket: asString(record.storage_bucket),
    storage_key: asString(record.storage_key),
    processing_status: asString(record.processing_status),
    page_count: asOptionalNumber(record.page_count),
    created_at: asString(record.created_at),
    updated_at: asString(record.updated_at),
    uploaded_by_staff_user_name: asString(record.uploaded_by_staff_user_name),
    uploaded_by_staff_user_id: asString(record.uploaded_by_staff_user_id),
  };
}

function normalizeDocumentsResponse(payload: unknown): LoadDocument[] {
  const root = asRecord(payload);

  if (!root) {
    return [];
  }

  const candidates = Array.isArray(root.data)
    ? root.data
    : Array.isArray(root.items)
      ? root.items
      : Array.isArray(payload)
        ? payload
        : [];

  return candidates
    .map((item) => normalizeDocument(item))
    .filter((item): item is LoadDocument => item !== null);
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

function formatFileSize(value?: number | null): string {
  if (value === undefined || value === null || !Number.isFinite(value) || value < 0) {
    return "—";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  if (value < 1024 * 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function processingStatusBadge(status?: string | null) {
  switch ((status ?? "").trim().toLowerCase()) {
    case "completed":
      return "bg-emerald-100 text-emerald-800";
    case "processing":
    case "in_progress":
    case "in-progress":
      return "bg-indigo-100 text-indigo-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    case "pending":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function normalizeDocumentTypeLabel(value?: string | null) {
  const normalized = (value ?? "").trim().toLowerCase();

  switch (normalized) {
    case "ratecon":
    case "rate_confirmation":
    case "rate-confirmation":
    case "rate confirmation":
      return "Rate Confirmation";
    case "bol":
    case "bill_of_lading":
    case "bill-of-lading":
    case "bill of lading":
      return "Bill of Lading";
    case "invoice":
      return "Invoice";
    case "pod":
    case "proof_of_delivery":
    case "proof-of-delivery":
    case "proof of delivery":
      return "Proof of Delivery";
    case "unknown":
      return "Unknown";
    default:
      return value && value.trim().length > 0 ? value : "Unknown";
  }
}

function getDocumentDisplayName(document: LoadDocument) {
  if (document.original_filename && document.original_filename.trim().length > 0) {
    return document.original_filename.trim();
  }

  return `${normalizeDocumentTypeLabel(document.document_type)} Document`;
}

export default function DocumentsPage() {
  const router = useRouter();

  const [documents, setDocuments] = useState<LoadDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadDocuments() {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setErrorMessage("Missing session context. Please sign in again.");
      setDocuments([]);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage(null);

      const payload = await apiClient.get<ApiResponse<unknown>>(
        "/documents?page=1&page_size=100",
        {
          token,
          organizationId,
        }
      );

      setDocuments(normalizeDocumentsResponse(payload));
    } catch (error) {
      setDocuments([]);
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : "Failed to load documents."
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, []);

  const metrics = useMemo(() => {
    const total = documents.length;
    const pending = documents.filter(
      (document) => (document.processing_status ?? "").toLowerCase() === "pending"
    ).length;
    const processing = documents.filter((document) =>
      ["processing", "in_progress", "in-progress"].includes(
        (document.processing_status ?? "").toLowerCase()
      )
    ).length;
    const completed = documents.filter(
      (document) => (document.processing_status ?? "").toLowerCase() === "completed"
    ).length;

    return {
      total,
      pending,
      processing,
      completed,
    };
  }, [documents]);

  function openDocument(documentId: string) {
    router.push(`/dashboard/documents/${documentId}`);
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Documents</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Documents</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Review uploaded documents, processing status, classification results, and
              linked operational records across the system.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void loadDocuments()}
              disabled={isLoading}
              className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-soft transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total documents</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : metrics.total}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Pending</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">
              {isLoading ? "..." : metrics.pending}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Processing</div>
            <div className="mt-2 text-3xl font-bold text-indigo-700">
              {isLoading ? "..." : metrics.processing}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Completed</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">
              {isLoading ? "..." : metrics.completed}
            </div>
          </div>
        </section>

        {errorMessage ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-rose-800">
                  Unable to load documents
                </h2>
                <p className="mt-1 text-sm text-rose-700">{errorMessage}</p>
              </div>

              <button
                type="button"
                onClick={() => void loadDocuments()}
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
                  <th className="px-5 py-4 font-semibold">Document</th>
                  <th className="px-5 py-4 font-semibold">Type</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Linked Load</th>
                  <th className="px-5 py-4 font-semibold">Size</th>
                  <th className="px-5 py-4 font-semibold">Uploaded</th>
                  <th className="px-5 py-4 font-semibold">Source</th>
                  <th className="px-5 py-4 font-semibold">Uploaded By</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={9} className="px-5 py-10 text-center text-slate-500">
                      Loading documents...
                    </td>
                  </tr>
                ) : documents.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-5 py-10 text-center text-slate-500">
                      No documents found. Upload from Driver Portal or seed demo records using{" "}
                      <code className="rounded bg-slate-100 px-1 py-0.5">make seed-dev-data</code>.
                    </td>
                  </tr>
                ) : (
                  documents.map((document) => (
                    <tr key={document.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4 align-top">
                        <div className="font-semibold text-slate-900">
                          {getDocumentDisplayName(document)}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">{document.id}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {document.mime_type ?? "Unknown MIME"}
                        </div>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                          {normalizeDocumentTypeLabel(document.document_type)}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${processingStatusBadge(
                            document.processing_status
                          )}`}
                        >
                          {(document.processing_status ?? "unknown").replaceAll("_", " ")}
                        </span>
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {document.load_id ?? "—"}
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {formatFileSize(document.file_size_bytes)}
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {formatDateTime(document.created_at)}
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {(document.source_channel ?? "unknown").replaceAll("_", " ")}
                      </td>

                      <td className="px-5 py-4 align-top text-slate-700">
                        {document.uploaded_by_staff_user_name ?? document.uploaded_by_staff_user_id ?? "System / Driver"}
                      </td>

                      <td className="px-5 py-4 align-top">
                        <button
                          type="button"
                          onClick={() => openDocument(document.id)}
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

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            This page provides the main document operations workspace. Upload actions may
            continue from load detail where documents are linked directly to a load.
          </p>
        </section>
      </div>
    </div>
  );
}
