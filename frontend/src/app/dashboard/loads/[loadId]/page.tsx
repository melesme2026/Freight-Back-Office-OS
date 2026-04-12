"use client";

import { useRouter, useParams } from "next/navigation";
import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type LoadStatus =
  | "new"
  | "docs_received"
  | "extracting"
  | "needs_review"
  | "validated"
  | "ready_to_submit"
  | "submitted"
  | "funded"
  | "paid"
  | "exception"
  | "archived";

type Load = {
  id: string;
  load_number: string | null;
  status: LoadStatus;
  driver_id?: string | null;
  driver_name?: string | null;
  broker_id?: string | null;
  broker_name?: string | null;
  broker_name_raw?: string | null;
  broker_email_raw?: string | null;
  customer_account_id?: string | null;
  customer_account_name?: string | null;
  pickup_location?: string | null;
  delivery_location?: string | null;
  gross_amount?: number | string | null;
  currency_code?: string | null;
  has_ratecon?: boolean | null;
  has_bol?: boolean | null;
  has_invoice?: boolean | null;
  notes?: string | null;
  last_reviewed_by?: string | null;
  last_reviewed_by_name?: string | null;
  last_reviewed_at?: string | null;
  submitted_at?: string | null;
  funded_at?: string | null;
  paid_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  factoring_notes?: string | null;
  paid_amount?: number | string | null;
  amount_received?: number | string | null;
  factoring_provider?: string | null;
  is_factored?: boolean | null;
};

type ReviewQueueItem = {
  load_id: string;
  load_number?: string;
  issue_count: number;
  primary_issue?: string;
  severity?: string;
  blocking_issue_count?: number;
  warning_issue_count?: number;
};

type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
  error?: ApiError | null;
};

type StatusTransitionResponse = {
  id: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
};

type MarkReviewedResponse = {
  id: string;
  last_reviewed_by?: string | null;
  last_reviewed_at?: string | null;
  updated_at?: string | null;
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
};

type UploadDocumentType =
  | ""
  | "ratecon"
  | "bol"
  | "invoice"
  | "pod"
  | "unknown";

const NEXT_STATUS_MAP: Partial<Record<LoadStatus, LoadStatus>> = {
  new: "docs_received",
  docs_received: "extracting",
  extracting: "needs_review",
  needs_review: "validated",
  validated: "ready_to_submit",
  ready_to_submit: "submitted",
  submitted: "funded",
  funded: "paid",
};

const WORKFLOW_ORDER: LoadStatus[] = [
  "new",
  "docs_received",
  "extracting",
  "needs_review",
  "validated",
  "ready_to_submit",
  "submitted",
  "funded",
  "paid",
];

const UPLOAD_DOCUMENT_TYPE_OPTIONS: Array<{
  value: UploadDocumentType;
  label: string;
}> = [
  { value: "", label: "Auto / Unknown" },
  { value: "ratecon", label: "Rate Confirmation" },
  { value: "bol", label: "Bill of Lading" },
  { value: "invoice", label: "Invoice" },
  { value: "pod", label: "Proof of Delivery" },
  { value: "unknown", label: "Other / Unknown" },
];

function statusBadge(status: string) {
  switch (status) {
    case "needs_review":
      return "bg-amber-100 text-amber-800";
    case "validated":
      return "bg-emerald-100 text-emerald-800";
    case "submitted":
      return "bg-blue-100 text-blue-800";
    case "paid":
      return "bg-purple-100 text-purple-800";
    case "docs_received":
      return "bg-cyan-100 text-cyan-800";
    case "extracting":
      return "bg-indigo-100 text-indigo-800";
    case "ready_to_submit":
      return "bg-sky-100 text-sky-800";
    case "funded":
      return "bg-violet-100 text-violet-800";
    case "exception":
      return "bg-rose-100 text-rose-800";
    case "archived":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function issueBadge(severity?: string) {
  switch ((severity ?? "").toLowerCase()) {
    case "high":
      return "bg-rose-100 text-rose-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    case "low":
      return "bg-emerald-100 text-emerald-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
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

function formatCurrency(value?: number | string | null, currencyCode = "USD") {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  const numericValue = typeof value === "string" ? Number.parseFloat(value) : value;

  if (!Number.isFinite(numericValue)) {
    return String(value);
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode || "USD",
    }).format(numericValue);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(numericValue);
  }
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function formatFileSize(value?: number | null) {
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

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function getStringField(record: Record<string, unknown> | null, key: string): string | null {
  if (!record) {
    return null;
  }

  const value = record[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

function getFirstStringField(
  record: Record<string, unknown> | null,
  keys: string[]
): string | null {
  for (const key of keys) {
    const value = getStringField(record, key);
    if (value) {
      return value;
    }
  }
  return null;
}

function getOptionalBooleanField(
  record: Record<string, unknown> | null,
  key: string
): boolean | null | undefined {
  if (!record || !(key in record)) {
    return undefined;
  }

  const value = record[key];

  if (typeof value === "boolean") {
    return value;
  }
  if (value === null) {
    return null;
  }
  if (typeof value === "number") {
    if (value === 1) {
      return true;
    }
    if (value === 0) {
      return false;
    }
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "true" || normalized === "1" || normalized === "yes") {
      return true;
    }
    if (normalized === "false" || normalized === "0" || normalized === "no") {
      return false;
    }
  }

  return null;
}

function getFirstOptionalBooleanField(
  record: Record<string, unknown> | null,
  keys: string[]
): boolean | null | undefined {
  if (!record) {
    return undefined;
  }

  for (const key of keys) {
    const value = getOptionalBooleanField(record, key);
    if (value !== undefined) {
      return value;
    }
  }

  return undefined;
}

function getOptionalNumericOrStringField(
  record: Record<string, unknown> | null,
  key: string
): number | string | null | undefined {
  if (!record || !(key in record)) {
    return undefined;
  }

  const value = record[key];
  if (typeof value === "number" || typeof value === "string" || value === null) {
    return value;
  }

  return null;
}

function getFirstOptionalNumericOrStringField(
  record: Record<string, unknown> | null,
  keys: string[]
): number | string | null | undefined {
  if (!record) {
    return undefined;
  }

  for (const key of keys) {
    const value = getOptionalNumericOrStringField(record, key);
    if (value !== undefined) {
      return value;
    }
  }

  return undefined;
}

function getOptionalNumberField(
  record: Record<string, unknown> | null,
  key: string
): number | null | undefined {
  if (!record || !(key in record)) {
    return undefined;
  }

  const value = record[key];
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  if (value === null) {
    return null;
  }

  return null;
}

function normalizeLoadStatus(value: unknown): LoadStatus {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";

  switch (normalized) {
    case "new":
    case "docs_received":
    case "extracting":
    case "needs_review":
    case "validated":
    case "ready_to_submit":
    case "submitted":
    case "funded":
    case "paid":
    case "exception":
    case "archived":
      return normalized;
    default:
      return "new";
  }
}

function normalizeSeverity(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const normalized = value.trim().toLowerCase();
  return normalized.length > 0 ? normalized : undefined;
}

function normalizeCount(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return Math.floor(value);
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return Math.floor(parsed);
    }
  }
  return 0;
}

function normalizeLoad(payload: unknown): Load | null {
  const record = asRecord(payload);
  const id = getStringField(record, "id");

  if (!id) {
    return null;
  }

  return {
    id,
    load_number: getStringField(record, "load_number"),
    status: normalizeLoadStatus(record?.status),
    driver_id: getStringField(record, "driver_id"),
    driver_name: getFirstStringField(record, ["driver_name", "driver_display_name"]),
    broker_id: getStringField(record, "broker_id"),
    broker_name: getStringField(record, "broker_name"),
    broker_name_raw: getFirstStringField(record, ["broker_name_raw", "broker_name"]),
    broker_email_raw: getStringField(record, "broker_email_raw"),
    customer_account_id: getStringField(record, "customer_account_id"),
    customer_account_name: getFirstStringField(record, [
      "customer_account_name",
      "customer_name",
    ]),
    pickup_location: getStringField(record, "pickup_location"),
    delivery_location: getStringField(record, "delivery_location"),
    gross_amount: getOptionalNumericOrStringField(record, "gross_amount"),
    currency_code: getStringField(record, "currency_code"),
    has_ratecon: getOptionalBooleanField(record, "has_ratecon"),
    has_bol: getOptionalBooleanField(record, "has_bol"),
    has_invoice: getOptionalBooleanField(record, "has_invoice"),
    notes: getStringField(record, "notes"),
    last_reviewed_by: getStringField(record, "last_reviewed_by"),
    last_reviewed_by_name: getStringField(record, "last_reviewed_by_name"),
    last_reviewed_at: getStringField(record, "last_reviewed_at"),
    submitted_at: getStringField(record, "submitted_at"),
    funded_at: getStringField(record, "funded_at"),
    paid_at: getStringField(record, "paid_at"),
    created_at: getStringField(record, "created_at"),
    updated_at: getStringField(record, "updated_at"),
    factoring_notes: getFirstStringField(record, ["factoring_notes", "payment_notes"]),
    paid_amount: getFirstOptionalNumericOrStringField(record, ["paid_amount"]),
    amount_received: getFirstOptionalNumericOrStringField(record, [
      "amount_received",
      "received_amount",
    ]),
    factoring_provider: getFirstStringField(record, [
      "factoring_provider",
      "factor_name",
      "factoring_company_name",
    ]),
    is_factored: getFirstOptionalBooleanField(record, ["is_factored", "factored"]),
  };
}

function normalizeReviewQueueItem(payload: unknown): ReviewQueueItem | null {
  const record = asRecord(payload);
  const loadId = getStringField(record, "load_id");

  if (!loadId) {
    return null;
  }

  return {
    load_id: loadId,
    load_number: getStringField(record, "load_number") ?? undefined,
    issue_count: normalizeCount(record?.issue_count),
    primary_issue: getStringField(record, "primary_issue") ?? undefined,
    severity: normalizeSeverity(record?.severity),
    blocking_issue_count: normalizeCount(record?.blocking_issue_count),
    warning_issue_count: normalizeCount(record?.warning_issue_count),
  };
}

function normalizeDocument(payload: unknown): LoadDocument | null {
  const record = asRecord(payload);
  const id = getStringField(record, "id");
  const organizationId = getStringField(record, "organization_id");
  const customerAccountId = getStringField(record, "customer_account_id");

  if (!id || !organizationId || !customerAccountId) {
    return null;
  }

  return {
    id,
    organization_id: organizationId,
    customer_account_id: customerAccountId,
    driver_id: getStringField(record, "driver_id"),
    load_id: getStringField(record, "load_id"),
    source_channel: getStringField(record, "source_channel"),
    document_type: getStringField(record, "document_type"),
    original_filename: getStringField(record, "original_filename"),
    mime_type: getStringField(record, "mime_type"),
    file_size_bytes: getOptionalNumberField(record, "file_size_bytes"),
    storage_bucket: getStringField(record, "storage_bucket"),
    storage_key: getStringField(record, "storage_key"),
    processing_status: getStringField(record, "processing_status"),
    page_count: getOptionalNumberField(record, "page_count"),
    created_at: getStringField(record, "created_at"),
    updated_at: getStringField(record, "updated_at"),
  };
}

function extractStaffUserId(payload: unknown): string | null {
  const root = asRecord(payload);
  if (!root) {
    return null;
  }

  const directStaffUserId = getStringField(root, "staff_user_id");
  if (directStaffUserId) {
    return directStaffUserId;
  }

  const directId = getStringField(root, "id");
  if (directId) {
    return directId;
  }

  const user = asRecord(root.user);
  const userStaffUserId = getStringField(user, "staff_user_id");
  if (userStaffUserId) {
    return userStaffUserId;
  }

  const userId = getStringField(user, "id");
  if (userId) {
    return userId;
  }

  const staffUser = asRecord(root.staff_user);
  const nestedStaffUserId = getStringField(staffUser, "id");
  if (nestedStaffUserId) {
    return nestedStaffUserId;
  }

  return null;
}

function normalizeLoadIdParam(value: string | string[] | undefined): string | null {
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }

  if (Array.isArray(value) && value.length > 0) {
    const first = value[0];
    if (typeof first === "string" && first.trim().length > 0) {
      return first.trim();
    }
  }

  return null;
}

function buildApiUrl(path: string) {
  const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/+$/, "");
  const versionPrefix = (process.env.NEXT_PUBLIC_API_VERSION_PREFIX ?? "/api/v1")
    .trim()
    .replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (baseUrl) {
    return `${baseUrl}${versionPrefix}${normalizedPath}`;
  }

  return `${versionPrefix}${normalizedPath}`;
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

function matchesDocumentType(document: LoadDocument, aliases: string[]): boolean {
  const normalized = (document.document_type ?? "").trim().toLowerCase();
  return aliases.includes(normalized);
}

function getLoadDisplayTitle(load: Load) {
  return load.load_number ?? load.id;
}

function getOperationalDisplayValue(primary?: string | null, fallback?: string | null) {
  if (primary && primary.trim().length > 0) {
    return primary;
  }
  if (fallback && fallback.trim().length > 0) {
    return fallback;
  }
  return "—";
}

function getPaymentStageLabel(load: Load) {
  if (load.status === "paid" || load.paid_at) {
    return "Paid";
  }
  if (load.status === "funded" || load.funded_at) {
    return load.is_factored ? "Factored / Funded" : "Funded";
  }
  if (load.status === "submitted" || load.submitted_at) {
    return "Submitted";
  }
  return "Not yet submitted";
}

function extractErrorMessage(caught: unknown, fallback: string) {
  if (caught instanceof Error && caught.message.trim().length > 0) {
    return caught.message;
  }
  return fallback;
}

export default function LoadDetailPage() {
  const router = useRouter();
  const params = useParams<{ loadId: string | string[] }>();
  const loadId = normalizeLoadIdParam(params?.loadId);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [load, setLoad] = useState<Load | null>(null);
  const [reviewQueueItem, setReviewQueueItem] = useState<ReviewQueueItem | null>(null);
  const [loadDocuments, setLoadDocuments] = useState<LoadDocument[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAdvancing, setIsAdvancing] = useState<boolean>(false);
  const [isMarkingReviewed, setIsMarkingReviewed] = useState<boolean>(false);
  const [isDocumentsLoading, setIsDocumentsLoading] = useState<boolean>(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState<boolean>(false);
  const [downloadingDocumentId, setDownloadingDocumentId] = useState<string | null>(null);
  const [selectedUploadDocumentType, setSelectedUploadDocumentType] =
    useState<UploadDocumentType>("");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchLoad = useCallback(async (): Promise<Load | null> => {
    if (!loadId) {
      return null;
    }

    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>(
      `/loads/${encodeURIComponent(loadId)}`,
      {
        token: token ?? undefined,
      }
    );

    return normalizeLoad(response.data);
  }, [loadId]);

  const fetchReviewQueueItem = useCallback(async (): Promise<ReviewQueueItem | null> => {
    if (!loadId) {
      return null;
    }

    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>("/review-queue", {
      token: token ?? undefined,
    });

    const items = Array.isArray(response.data) ? response.data : [];
    for (const item of items) {
      const normalized = normalizeReviewQueueItem(item);
      if (normalized && normalized.load_id === loadId) {
        return normalized;
      }
    }

    return null;
  }, [loadId]);

  const fetchLoadDocuments = useCallback(
    async (options?: { silent?: boolean }): Promise<LoadDocument[]> => {
      if (!loadId) {
        setLoadDocuments([]);
        return [];
      }

      try {
        if (!options?.silent) {
          setIsDocumentsLoading(true);
        }

        const token = getAccessToken();
        const response = await apiClient.get<ApiResponse<unknown>>(
          `/loads/${encodeURIComponent(loadId)}/documents?page=1&page_size=100`,
          {
            token: token ?? undefined,
          }
        );

        const items = Array.isArray(response.data) ? response.data : [];
        const normalizedDocuments = items
          .map((item) => normalizeDocument(item))
          .filter((item): item is LoadDocument => item !== null);

        setLoadDocuments(normalizedDocuments);
        return normalizedDocuments;
      } finally {
        setIsDocumentsLoading(false);
      }
    },
    [loadId]
  );

  const fetchCurrentStaffUserId = useCallback(async (): Promise<string> => {
    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>("/auth/me", {
      token: token ?? undefined,
    });

    const staffUserId = extractStaffUserId(response.data);
    if (!staffUserId) {
      throw new Error("Unable to determine current staff user ID.");
    }

    return staffUserId;
  }, []);

  const fetchPageData = useCallback(async () => {
    if (!loadId) {
      setLoad(null);
      setReviewQueueItem(null);
      setLoadDocuments([]);
      setError("Invalid load identifier.");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const [loadData, reviewItem, documents] = await Promise.all([
        fetchLoad(),
        fetchReviewQueueItem().catch(() => null),
        fetchLoadDocuments({ silent: true }).catch(() => []),
      ]);

      setLoad(loadData);
      setReviewQueueItem(reviewItem);
      setLoadDocuments(documents);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to fetch load."));
    } finally {
      setIsLoading(false);
      setIsDocumentsLoading(false);
    }
  }, [fetchLoad, fetchReviewQueueItem, fetchLoadDocuments, loadId]);

  useEffect(() => {
    void fetchPageData();
  }, [fetchPageData]);

  const nextStatus = useMemo(() => {
    if (!load) {
      return null;
    }
    return NEXT_STATUS_MAP[load.status] ?? null;
  }, [load]);

  const documentPresence = useMemo(() => {
    const hasRateConFromDocuments = loadDocuments.some((document) =>
      matchesDocumentType(document, [
        "ratecon",
        "rate_confirmation",
        "rate-confirmation",
        "rate confirmation",
      ])
    );

    const hasBolFromDocuments = loadDocuments.some((document) =>
      matchesDocumentType(document, [
        "bol",
        "bill_of_lading",
        "bill-of-lading",
        "bill of lading",
      ])
    );

    const hasInvoiceFromDocuments = loadDocuments.some((document) =>
      matchesDocumentType(document, ["invoice"])
    );

    return {
      hasRateCon: load?.has_ratecon === true || hasRateConFromDocuments,
      hasBol: load?.has_bol === true || hasBolFromDocuments,
      hasInvoice: load?.has_invoice === true || hasInvoiceFromDocuments,
    };
  }, [load, loadDocuments]);

  const requiredDocsReceivedCount = useMemo(() => {
    return [documentPresence.hasRateCon, documentPresence.hasBol, documentPresence.hasInvoice].filter(
      Boolean
    ).length;
  }, [documentPresence]);

  const documentChecklist = useMemo(
    () => [
      {
        name: "Rate Confirmation",
        status: documentPresence.hasRateCon ? "received" : "missing",
      },
      {
        name: "Bill of Lading",
        status: documentPresence.hasBol ? "received" : "missing",
      },
      {
        name: "Invoice",
        status: documentPresence.hasInvoice ? "received" : "missing",
      },
    ],
    [documentPresence]
  );

  const validationIssues = useMemo(() => {
    const issues = new Map<string, string>();

    if (reviewQueueItem?.primary_issue && reviewQueueItem.primary_issue.trim().length > 0) {
      const value = reviewQueueItem.primary_issue.trim();
      issues.set(value.toLowerCase(), value);
    }

    if (!documentPresence.hasInvoice) {
      issues.set("invoice missing", "Invoice missing");
    }
    if (!documentPresence.hasRateCon) {
      issues.set("rate confirmation missing", "Rate confirmation missing");
    }
    if (!documentPresence.hasBol) {
      issues.set("bill of lading missing", "Bill of lading missing");
    }

    return Array.from(issues.values());
  }, [documentPresence, reviewQueueItem]);

  const totalOpenIssues = useMemo(() => {
    if (reviewQueueItem && reviewQueueItem.issue_count > 0) {
      return reviewQueueItem.issue_count;
    }
    return validationIssues.length;
  }, [reviewQueueItem, validationIssues]);

  const workflowBlockedReason = useMemo(() => {
    if (!load || !nextStatus) {
      return null;
    }

    if (
      (nextStatus === "validated" ||
        nextStatus === "ready_to_submit" ||
        nextStatus === "submitted") &&
      totalOpenIssues > 0
    ) {
      return "Resolve open validation issues before advancing this load.";
    }

    if (
      (nextStatus === "ready_to_submit" || nextStatus === "submitted") &&
      requiredDocsReceivedCount < 3
    ) {
      return "All required documents must be present before submission readiness.";
    }

    return null;
  }, [load, nextStatus, totalOpenIssues, requiredDocsReceivedCount]);

  const canAdvanceStatus = Boolean(nextStatus) && !workflowBlockedReason && !isAdvancing;

  const canUploadDocuments = useMemo(() => {
    return Boolean(load?.id && load?.customer_account_id && getOrganizationId());
  }, [load]);

  const workflowSteps = useMemo(() => {
    if (!load) {
      return [];
    }

    const currentIndex = WORKFLOW_ORDER.indexOf(load.status);

    return WORKFLOW_ORDER.map((status, index) => {
      const state =
        currentIndex === -1
          ? "upcoming"
          : index < currentIndex
            ? "completed"
            : index === currentIndex
              ? "current"
              : "upcoming";

      return { status, state };
    });
  }, [load]);

  async function handleMarkReviewed() {
    if (!load || !loadId || isMarkingReviewed) {
      return;
    }

    try {
      setIsMarkingReviewed(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const staffUserId = await fetchCurrentStaffUserId();

      const response = await apiClient.post<ApiResponse<MarkReviewedResponse>>(
        `/review-queue/loads/${encodeURIComponent(load.id)}/mark-reviewed`,
        {
          staff_user_id: staffUserId,
        },
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();

      const reviewedAt = response.data?.last_reviewed_at;
      const message = reviewedAt
        ? `Load marked as reviewed at ${formatDateTime(reviewedAt)}.`
        : "Load marked as reviewed.";

      setActionMessage(message);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to mark load reviewed."));
    } finally {
      setIsMarkingReviewed(false);
    }
  }

  async function handleAdvanceStatus() {
    if (!load || !nextStatus || !canAdvanceStatus) {
      return;
    }

    try {
      setIsAdvancing(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const staffUserId = await fetchCurrentStaffUserId();

      const response = await apiClient.post<ApiResponse<StatusTransitionResponse>>(
        `/loads/${encodeURIComponent(load.id)}/status`,
        {
          new_status: nextStatus,
          actor_staff_user_id: staffUserId,
          actor_type: "staff_user",
          notes: `Advanced from UI to ${nextStatus}`,
        },
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();

      const resolvedStatus = response.data?.new_status ?? nextStatus;
      setActionMessage(`Status updated to ${resolvedStatus.replaceAll("_", " ")}.`);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to advance status."));
    } finally {
      setIsAdvancing(false);
    }
  }

  async function handleUploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;

    if (!file) {
      return;
    }

    if (!load?.id) {
      setError("Load is required before uploading documents.");
      event.target.value = "";
      return;
    }

    const organizationId = getOrganizationId();
    if (!organizationId) {
      setError("Organization context is missing. Please sign in again.");
      event.target.value = "";
      return;
    }

    if (!load.customer_account_id) {
      setError("Customer account is missing for this load. Cannot upload document.");
      event.target.value = "";
      return;
    }

    try {
      setIsUploadingDocument(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();

      const formData = new FormData();
      formData.append("organization_id", organizationId);
      formData.append("customer_account_id", load.customer_account_id);
      formData.append("source_channel", "manual");
      formData.append("load_id", load.id);
      formData.append("file", file);

      if (load.driver_id) {
        formData.append("driver_id", load.driver_id);
      }

      if (selectedUploadDocumentType) {
        formData.append("document_type", selectedUploadDocumentType);
      }

      const uploadResponse = await fetch(buildApiUrl("/documents/upload"), {
        method: "POST",
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
        body: formData,
      });

      if (!uploadResponse.ok) {
        const responseText = await uploadResponse.text();
        throw new Error(responseText || "Failed to upload document.");
      }

      const [updatedLoad, updatedDocuments] = await Promise.all([
        fetchLoad(),
        fetchLoadDocuments({ silent: true }),
      ]);

      setLoad(updatedLoad);
      setLoadDocuments(updatedDocuments);
      setSelectedUploadDocumentType("");
      setActionMessage(`Document "${file.name}" uploaded successfully.`);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to upload document."));
    } finally {
      setIsUploadingDocument(false);
      if (event.target) {
        event.target.value = "";
      }
    }
  }

  async function handleDownloadDocument(document: LoadDocument) {
    if (!document.id || downloadingDocumentId) {
      return;
    }

    try {
      setDownloadingDocumentId(document.id);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();

      const response = await fetch(
        buildApiUrl(`/documents/${encodeURIComponent(document.id)}/download`),
        {
          method: "GET",
          headers: token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : undefined,
        }
      );

      if (!response.ok) {
        const responseText = await response.text();
        throw new Error(responseText || "Failed to download document.");
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = blobUrl;
      link.download = getDocumentDisplayName(document);
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);

      setActionMessage(`Downloaded ${getDocumentDisplayName(document)}.`);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to download document."));
    } finally {
      setDownloadingDocumentId(null);
    }
  }

  function handleBackToLoads() {
    router.push("/dashboard/loads");
  }

  function handleOpenReviewQueue() {
    router.push("/dashboard/review-queue");
  }

  function handleGoBack() {
    router.back();
  }

  function handleOpenFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleRefreshDocuments() {
    try {
      setError(null);
      setActionMessage(null);

      const [updatedLoad, updatedDocuments] = await Promise.all([
        fetchLoad(),
        fetchLoadDocuments(),
      ]);

      setLoad(updatedLoad);
      setLoadDocuments(updatedDocuments);
      setActionMessage("Documents refreshed.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to refresh documents."));
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">Loading load...</h1>
            <p className="mt-3 text-sm text-slate-600">
              Fetching load summary, review queue status, document completeness, and payment state.
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (error && !load) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">Unable to load load detail</h1>
            <p className="mt-2 text-sm text-rose-700">{error}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleGoBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={handleBackToLoads}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Loads
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!load) {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">Load not found</h1>
            <p className="mt-2 text-sm text-rose-700">
              No load matched the requested identifier.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleGoBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={handleBackToLoads}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Back to Loads
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {getLoadDisplayTitle(load)}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Full operational view of a load, including documents, validation issues, workflow
              progress, and payment visibility.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleMarkReviewed}
              disabled={isMarkingReviewed}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isMarkingReviewed ? "Marking..." : "Mark Reviewed"}
            </button>

            <button
              type="button"
              onClick={handleAdvanceStatus}
              disabled={!canAdvanceStatus}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isAdvancing
                ? "Advancing..."
                : nextStatus
                  ? `Advance to ${nextStatus.replaceAll("_", " ")}`
                  : "No Further Status"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {actionMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {actionMessage}
          </div>
        ) : null}

        {workflowBlockedReason ? (
          <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {workflowBlockedReason}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">Load Summary</h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                    load.status
                  )}`}
                >
                  {load.status.replaceAll("_", " ")}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Driver</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {getOperationalDisplayValue(load.driver_name, load.driver_id)}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Broker</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {getOperationalDisplayValue(load.broker_name_raw, load.broker_id)}
                  </div>
                  {load.broker_email_raw ? (
                    <div className="mt-1 text-xs text-slate-500">{load.broker_email_raw}</div>
                  ) : null}
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {getOperationalDisplayValue(load.customer_account_name, load.customer_account_id)}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Gross Amount
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatCurrency(load.gross_amount, load.currency_code ?? "USD")}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Pickup</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.pickup_location ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Delivery</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.delivery_location ?? "—"}
                  </div>
                </div>
              </div>

              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Last Reviewed By
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.last_reviewed_by_name ?? load.last_reviewed_by ?? "—"}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Last Reviewed At
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(load.last_reviewed_at)}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Created</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(load.created_at)}
                  </div>
                </div>

                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Updated</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {formatDateTime(load.updated_at)}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Workflow Readiness</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Current lane status, readiness blockers, and lifecycle progression.
                  </p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                    load.status
                  )}`}
                >
                  {load.status.replaceAll("_", " ")}
                </span>
              </div>

              <div className="mb-6 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-200 px-4 py-3">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Open Issues</div>
                  <div className="mt-1 text-lg font-semibold text-slate-950">{totalOpenIssues}</div>
                </div>
                <div className="rounded-xl border border-slate-200 px-4 py-3">
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Required Docs Received
                  </div>
                  <div className="mt-1 text-lg font-semibold text-slate-950">
                    {requiredDocsReceivedCount}/3
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 px-4 py-3">
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Payment Stage
                  </div>
                  <div className="mt-1 text-lg font-semibold text-slate-950">
                    {getPaymentStageLabel(load)}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                {workflowSteps.map((step) => (
                  <div
                    key={step.status}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-slate-900">
                      {step.status.replaceAll("_", " ")}
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        step.state === "completed"
                          ? "bg-emerald-100 text-emerald-800"
                          : step.state === "current"
                            ? "bg-brand-100 text-brand-800"
                            : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {step.state}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Documents</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Upload, review, and download load documents from a single place.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleRefreshDocuments}
                    disabled={isDocumentsLoading || isUploadingDocument}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isDocumentsLoading ? "Refreshing..." : "Refresh Documents"}
                  </button>

                  <button
                    type="button"
                    onClick={handleOpenFilePicker}
                    disabled={!canUploadDocuments || isUploadingDocument}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isUploadingDocument ? "Uploading..." : "Upload Document"}
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg,.webp,.heic,.heif,.tif,.tiff"
                    onChange={handleUploadDocument}
                  />
                </div>
              </div>

              <div className="mb-5 grid gap-4 lg:grid-cols-[240px,1fr]">
                <div>
                  <label
                    htmlFor="documentType"
                    className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500"
                  >
                    Upload Document Type
                  </label>
                  <select
                    id="documentType"
                    value={selectedUploadDocumentType}
                    onChange={(event) =>
                      setSelectedUploadDocumentType(event.target.value as UploadDocumentType)
                    }
                    disabled={isUploadingDocument}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {UPLOAD_DOCUMENT_TYPE_OPTIONS.map((option) => (
                      <option key={option.value || "auto"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  {!canUploadDocuments ? (
                    <span>
                      Upload is unavailable until organization context, customer account, and load
                      linkage are present.
                    </span>
                  ) : (
                    <span>
                      Supported uploads: PDF and common image formats. Documents will be attached
                      directly to this load and available for download below.
                    </span>
                  )}
                </div>
              </div>

              <div className="mb-6 grid gap-3 sm:grid-cols-3">
                {documentChecklist.map((document) => (
                  <div
                    key={document.name}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-slate-900">{document.name}</div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        document.status === "received"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {document.status}
                    </span>
                  </div>
                ))}
              </div>

              <div className="rounded-2xl border border-slate-200">
                <div className="grid grid-cols-12 gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <div className="col-span-12 lg:col-span-4">Document</div>
                  <div className="col-span-6 lg:col-span-2">Type</div>
                  <div className="col-span-6 lg:col-span-2">Status</div>
                  <div className="col-span-6 lg:col-span-2">Uploaded</div>
                  <div className="col-span-6 lg:col-span-1">Size</div>
                  <div className="col-span-12 lg:col-span-1 text-right">Action</div>
                </div>

                {loadDocuments.length > 0 ? (
                  <div className="divide-y divide-slate-200">
                    {loadDocuments.map((document) => (
                      <div
                        key={document.id}
                        className="grid grid-cols-12 gap-3 px-4 py-4 text-sm text-slate-700"
                      >
                        <div className="col-span-12 lg:col-span-4">
                          <div className="font-medium text-slate-900">
                            {getDocumentDisplayName(document)}
                          </div>
                          <div className="mt-1 text-xs text-slate-500">
                            {document.mime_type ?? "Unknown MIME"}
                          </div>
                        </div>

                        <div className="col-span-6 lg:col-span-2">
                          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                            {normalizeDocumentTypeLabel(document.document_type)}
                          </span>
                        </div>

                        <div className="col-span-6 lg:col-span-2">
                          <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold ${processingStatusBadge(
                              document.processing_status
                            )}`}
                          >
                            {(document.processing_status ?? "unknown").replaceAll("_", " ")}
                          </span>
                        </div>

                        <div className="col-span-6 lg:col-span-2">
                          <div>{formatDateTime(document.created_at)}</div>
                        </div>

                        <div className="col-span-6 lg:col-span-1">
                          <div>{formatFileSize(document.file_size_bytes)}</div>
                        </div>

                        <div className="col-span-12 flex justify-end lg:col-span-1">
                          <button
                            type="button"
                            onClick={() => void handleDownloadDocument(document)}
                            disabled={downloadingDocumentId === document.id}
                            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {downloadingDocumentId === document.id ? "Downloading..." : "Download"}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-8 text-sm text-slate-500">
                    No documents are attached to this load yet.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-950">Validation Issues</h2>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {totalOpenIssues} open
                  </span>

                  {reviewQueueItem?.severity ? (
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${issueBadge(
                        reviewQueueItem.severity
                      )}`}
                    >
                      {reviewQueueItem.severity}
                    </span>
                  ) : null}
                </div>
              </div>

              {validationIssues.length > 0 ? (
                <div className="space-y-3">
                  {validationIssues.map((issue) => (
                    <div
                      key={issue}
                      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                    >
                      {issue}
                    </div>
                  ))}

                  {reviewQueueItem && reviewQueueItem.issue_count > validationIssues.length ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                      Additional unresolved validation items exist for this load. Open Review Queue
                      for the current review summary.
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-sm text-slate-500">No open validation issues.</div>
              )}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={handleOpenReviewQueue}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Review Queue
                </button>
                <button
                  type="button"
                  onClick={handleBackToLoads}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Back to Loads
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Load Metrics</h2>
              <div className="space-y-3 text-sm text-slate-700">
                <div className="flex items-center justify-between">
                  <span>Total Documents</span>
                  <span className="font-semibold text-slate-900">{loadDocuments.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Required Docs Received</span>
                  <span className="font-semibold text-slate-900">{requiredDocsReceivedCount}/3</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Load Status</span>
                  <span className="font-semibold text-slate-900">
                    {load.status.replaceAll("_", " ")}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Open Issues</span>
                  <span className="font-semibold text-slate-900">{totalOpenIssues}</span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Payment / Factoring</h2>
              <div className="space-y-3 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-4">
                  <span>Stage</span>
                  <span className="font-semibold text-slate-900">{getPaymentStageLabel(load)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Submitted At</span>
                  <span className="font-medium text-slate-900">
                    {formatDateTime(load.submitted_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Funded At</span>
                  <span className="font-medium text-slate-900">{formatDateTime(load.funded_at)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Paid At</span>
                  <span className="font-medium text-slate-900">{formatDateTime(load.paid_at)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Paid Amount</span>
                  <span className="font-medium text-slate-900">
                    {formatCurrency(load.paid_amount, load.currency_code ?? "USD")}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Amount Received</span>
                  <span className="font-medium text-slate-900">
                    {formatCurrency(load.amount_received, load.currency_code ?? "USD")}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Factored</span>
                  <span className="font-medium text-slate-900">
                    {load.is_factored === true ? "Yes" : load.is_factored === false ? "No" : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Factor</span>
                  <span className="font-medium text-slate-900">
                    {load.factoring_provider ?? "—"}
                  </span>
                </div>
              </div>

              {load.factoring_notes ? (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  {load.factoring_notes}
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Notes</h2>
              <div className="text-sm text-slate-700">
                {load.notes && load.notes.trim().length > 0 ? load.notes : "No notes available."}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}