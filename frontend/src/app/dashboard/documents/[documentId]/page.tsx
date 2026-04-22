"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

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

type ExtractedField = {
  field: string;
  value: string;
  confidence: string | null;
};

type DocumentDetailView = {
  id: string;
  originalFilename: string;
  documentType: string;
  processingStatus: string;
  sourceChannel: string;
  linkedLoad: string | null;
  uploadedBy: string | null;
  uploadedAt: string | null;
  classificationConfidence: string | null;
  extractedFields: ExtractedField[];
  validationIssues: string[];
  previewText: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown, fallback = "—"): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
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

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => asNullableString(item))
    .filter((item): item is string => item !== null);
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function formatConfidence(value: string | null): string {
  if (!value) {
    return "—";
  }

  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value;
  }

  if (numeric <= 1) {
    return numeric.toFixed(2);
  }

  return String(numeric);
}

function statusBadgeClass(status?: string): string {
  switch ((status ?? "").toLowerCase()) {
    case "completed":
    case "validated":
    case "linked":
      return "bg-emerald-100 text-emerald-800";
    case "processing":
    case "queued":
    case "in_progress":
    case "in-progress":
    case "pending":
      return "bg-amber-100 text-amber-800";
    case "failed":
    case "rejected":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function normalizeExtractedFields(
  value: unknown,
  fallbackRecord: Record<string, unknown> | null
): ExtractedField[] {
  if (Array.isArray(value)) {
    return value
      .map((item): ExtractedField | null => {
        const record = asRecord(item);
        if (!record) {
          return null;
        }

        const field =
          asNullableString(record.field) ??
          asNullableString(record.name) ??
          asNullableString(record.key) ??
          asNullableString(record.field_name);

        const fieldValue =
          asNullableString(record.value) ??
          asNullableString(record.extracted_value) ??
          asNullableString(record.normalized_value) ??
          asNullableString(record.field_value_text);

        if (!field || !fieldValue) {
          return null;
        }

        return {
          field,
          value: fieldValue,
          confidence:
            asNullableString(record.confidence) ??
            asNullableString(record.confidence_score),
        };
      })
      .filter((item): item is ExtractedField => item !== null);
  }

  if (fallbackRecord) {
    return Object.entries(fallbackRecord)
      .map(([field, rawValue]): ExtractedField | null => {
        const valueString = asNullableString(rawValue);
        if (!valueString) {
          return null;
        }

        return {
          field,
          value: valueString,
          confidence: null,
        };
      })
      .filter((item): item is ExtractedField => item !== null);
  }

  return [];
}

function normalizeDocumentDetail(
  payload: unknown,
  documentId: string
): DocumentDetailView | null {
  const root = asRecord(payload);
  if (!root) {
    return null;
  }

  const container =
    asRecord(root.data) ??
    asRecord(root.document) ??
    asRecord(root.item) ??
    root;

  const extractedFieldsRecord =
    asRecord(container.extracted_fields) ??
    asRecord(container.extractedFields);

  const previewText =
    asNullableString(container.preview_text) ??
    asNullableString(container.ocr_text) ??
    asNullableString(container.text_content) ??
    asNullableString(container.previewText) ??
    "";

  const validationIssues =
    asStringArray(container.validation_issues) ??
    asStringArray(container.validationIssues);

  const fallbackIssues = asStringArray(container.issues);

  return {
    id:
      asNullableString(container.id) ??
      asNullableString(container.document_id) ??
      documentId,
    originalFilename:
      asNullableString(container.original_filename) ??
      asNullableString(container.filename) ??
      asNullableString(container.file_name) ??
      "Unknown document",
    documentType:
      asNullableString(container.document_type) ??
      asNullableString(container.type) ??
      "unknown",
    processingStatus:
      asNullableString(container.processing_status) ??
      asNullableString(container.status) ??
      "unknown",
    sourceChannel:
      asNullableString(container.source_channel) ??
      asNullableString(container.source) ??
      "unknown",
    linkedLoad:
      asNullableString(container.load_id) ??
      asNullableString(container.linked_load) ??
      asNullableString(container.load_number),
    uploadedBy:
      asNullableString(container.uploaded_by) ??
      asNullableString(container.created_by) ??
      asNullableString(container.uploaded_by_staff_user_id),
    uploadedAt:
      asNullableString(container.uploaded_at) ??
      asNullableString(container.created_at),
    classificationConfidence:
      asNullableString(container.classification_confidence) ??
      asNullableString(container.confidence),
    extractedFields: normalizeExtractedFields(
      container.extracted_fields ?? container.extractedFields,
      extractedFieldsRecord
    ),
    validationIssues:
      validationIssues.length > 0 ? validationIssues : fallbackIssues,
    previewText,
  };
}

export default function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams();

  const rawDocumentId = params?.documentId;
  const documentId = Array.isArray(rawDocumentId)
    ? rawDocumentId[0] ?? ""
    : typeof rawDocumentId === "string"
      ? rawDocumentId
      : "";

  const [document, setDocument] = useState<DocumentDetailView | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadDocument() {
      if (!documentId) {
        if (isMounted) {
          setDocument(null);
          setError("Document ID is missing.");
          setIsLoading(false);
        }
        return;
      }

      const token = getAccessToken();
      const organizationId = getOrganizationId();

      if (!token || !organizationId) {
        if (isMounted) {
          setDocument(null);
          setError("Missing session context. Please sign in again.");
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const payload = await apiClient.get<ApiResponse<unknown>>(
          `/documents/${encodeURIComponent(documentId)}`,
          {
            token,
            organizationId,
          }
        );

        const normalized = normalizeDocumentDetail(payload, documentId);

        if (!normalized) {
          throw new Error("Document response could not be normalized.");
        }

        if (isMounted) {
          setDocument(normalized);
        }
      } catch (caught) {
        if (isMounted) {
          const message =
            caught instanceof Error
              ? caught.message
              : "An unexpected error occurred while loading the document.";
          setError(message);
          setDocument(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadDocument();

    return () => {
      isMounted = false;
    };
  }, [documentId]);

  const hasValidationIssues = useMemo(
    () => (document?.validationIssues.length ?? 0) > 0,
    [document]
  );
  const linkedLoadId = useMemo(() => {
    const value = document?.linkedLoad?.trim();
    if (!value) {
      return null;
    }

    return /^[0-9a-fA-F-]{36}$/.test(value) ? value : null;
  }, [document?.linkedLoad]);

  const handleBack = () => {
    router.back();
  };

  async function handleReprocessDocument() {
    if (!documentId) return;

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setActionError("Missing session context. Please sign in again.");
      return;
    }

    try {
      setIsReprocessing(true);
      setActionError(null);
      setActionMessage(null);

      await apiClient.post(
        `/documents/${encodeURIComponent(documentId)}/reprocess`,
        {
          force_reclassification: true,
          force_reextraction: true,
        },
        { token, organizationId }
      );

      setActionMessage("Document reprocessing requested.");
      router.refresh();
    } catch (caught: unknown) {
      setActionError(caught instanceof Error ? caught.message : "Unable to reprocess document.");
    } finally {
      setIsReprocessing(false);
    }
  }

  async function handleRunExtraction() {
    if (!documentId) return;

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setActionError("Missing session context. Please sign in again.");
      return;
    }

    try {
      setIsExtracting(true);
      setActionError(null);
      setActionMessage(null);

      await apiClient.post(
        `/documents/${encodeURIComponent(documentId)}/extract`,
        { force: true },
        { token, organizationId }
      );
      setActionMessage("Extraction requested. Refresh after processing completes.");
      router.refresh();
    } catch (caught: unknown) {
      setActionError(caught instanceof Error ? caught.message : "Unable to run extraction.");
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleDownloadOriginal() {
    if (!documentId) return;

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setActionError("Missing session context. Please sign in again.");
      return;
    }

    try {
      setIsDownloading(true);
      setActionError(null);
      setActionMessage(null);

      const blob = await apiClient.getBlob(
        `/documents/${encodeURIComponent(documentId)}/download`,
        { token, organizationId }
      );
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = downloadUrl;
      link.download = document?.originalFilename || `${documentId}.bin`;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      setActionMessage("Document download started.");
    } catch (caught: unknown) {
      setActionError(caught instanceof Error ? caught.message : "Unable to download original file.");
    } finally {
      setIsDownloading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Documents / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Loading document...
            </h1>
            <p className="mt-3 text-sm text-slate-600">
              Fetching document metadata, extracted fields, and validation results.
            </p>
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
              Dashboard / Documents / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">
              Unable to load document
            </h1>
            <p className="mt-2 text-sm text-rose-700">{error}</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>

              <Link
                href="/dashboard/documents"
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Open Documents
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Documents / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Document not found
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              No document matched ID:
            </p>
            <p className="mt-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-800">
              {documentId || "—"}
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>

              <Link
                href="/dashboard/documents"
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Open Documents
              </Link>
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
            onClick={handleBack}
            className="text-sm font-medium text-brand-700 hover:text-brand-800"
          >
            ← Back
          </button>
        </div>

        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Documents / Detail
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {document.originalFilename}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review document metadata, extracted fields, validation outcomes,
              and preview content.
            </p>
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
              Extraction/OCR may produce incomplete values for some files.
              Validate critical fields before operational decisions.
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleReprocessDocument()}
              disabled={isReprocessing || isExtracting}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isReprocessing ? "Reprocessing..." : "Reprocess"}
            </button>
            <button
              type="button"
              onClick={() => void handleRunExtraction()}
              disabled={isExtracting || isReprocessing}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isExtracting ? "Running..." : "Run Extraction"}
            </button>
          </div>
        </div>
        {actionError ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{actionError}</div>
        ) : null}
        {actionMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{actionMessage}</div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">
                  Document Summary
                </h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(
                    document.processingStatus
                  )}`}
                >
                  {asString(document.processingStatus, "unknown")}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Document Type
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {asString(document.documentType, "—")}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Source Channel
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {asString(document.sourceChannel, "—")}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Linked Load
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.linkedLoad ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Classification Confidence
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatConfidence(document.classificationConfidence)}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Uploaded By
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.uploadedBy ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Uploaded At
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(document.uploadedAt)}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Extracted Fields
              </h2>

              {document.extractedFields.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                  No extracted fields are available for this document yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {document.extractedFields.map((field) => (
                    <div
                      key={`${field.field}-${field.value}`}
                      className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-4 py-3"
                    >
                      <div className="min-w-0">
                        <div className="text-xs uppercase tracking-wide text-slate-500">
                          {field.field}
                        </div>
                        <div className="mt-1 break-words text-sm font-medium text-slate-900">
                          {field.value}
                        </div>
                      </div>

                      <div className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                        {formatConfidence(field.confidence)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Preview
              </h2>

              {document.previewText.trim().length > 0 ? (
                <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">
                  {document.previewText}
                </pre>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                  No preview text is available for this document.
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Validation Issues
              </h2>

              {hasValidationIssues ? (
                <div className="space-y-3">
                  {document.validationIssues.map((issue) => (
                    <div
                      key={issue}
                      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                    >
                      {issue}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  No validation issues found.
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Quick Actions
              </h2>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => router.push("/dashboard/review-queue")}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Review Queue (Field Corrections)
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/dashboard/review-queue")}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Resolve Validation Issues
                </button>
                <button
                  type="button"
                  onClick={() => void handleDownloadOriginal()}
                  disabled={isDownloading}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isDownloading ? "Downloading..." : "Download Original File"}
                </button>
                {linkedLoadId ? (
                  <Link
                    href={`/dashboard/loads/${linkedLoadId}`}
                    className="block rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                  >
                    Open Linked Load
                  </Link>
                ) : null}
                <Link
                  href="/dashboard/documents"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Documents
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
