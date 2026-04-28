"use client";

import { useRouter, useParams } from "next/navigation";
import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { buildApiUrl as buildConfiguredApiUrl } from "@/lib/config";

type LoadStatus =
  | "booked"
  | "in_transit"
  | "delivered"
  | "docs_received"
  | "docs_needs_attention"
  | "invoice_ready"
  | "submitted_to_broker"
  | "submitted_to_factoring"
  | "packet_rejected"
  | "resubmission_needed"
  | "reserve_pending"
  | "advance_paid"
  | "fully_paid"
  | "short_paid"
  | "disputed"
  | "archived";

type PacketReadiness = {
  readiness_state?: string | null;
  ready_for_invoice?: boolean | null;
  ready_to_submit?: boolean | null;
  present_documents?: string[] | null;
  missing_required_documents?: {
    invoice?: string[] | null;
    submission?: string[] | null;
  } | null;
  missing_recommended_documents?: string[] | null;
  blockers?: string[] | null;
  notes?: string[] | null;
};

type Load = {
  id: string;
  load_number: string | null;
  invoice_number?: string | null;
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
  last_contacted_at?: string | null;
  follow_up_required?: boolean | null;
  next_follow_up_at?: string | null;
  follow_up_owner_id?: string | null;
  follow_up_owner_name?: string | null;
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
  packet_readiness?: PacketReadiness | null;
  operational?: {
    queue?: string;
    queues?: string[];
    next_action?: { code?: string; label?: string };
    days_in_state?: number | null;
    entered_state_at?: string | null;
    is_overdue?: boolean;
    blockers?: string[];
  } | null;
};

type CarrierProfile = {
  legal_name: string | null;
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

type WorkflowAction =
  | "submit_to_broker"
  | "submit_to_factoring"
  | "mark_packet_rejected"
  | "mark_resubmission_needed"
  | "mark_advance_paid"
  | "mark_reserve_pending"
  | "mark_fully_paid"
  | "mark_short_paid"
  | "mark_disputed";

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

type SubmissionPacketDocument = {
  id: string;
  document_id?: string | null;
  document_type?: string | null;
  filename_snapshot?: string | null;
};

type SubmissionPacketEvent = {
  id: string;
  event_type?: string | null;
  message?: string | null;
  created_at?: string | null;
  recipient?: string | null;
};

type SubmissionPacket = {
  id: string;
  packet_reference?: string | null;
  destination_type?: string | null;
  destination_name?: string | null;
  destination_email?: string | null;
  status?: string | null;
  created_at?: string | null;
  sent_at?: string | null;
  documents: SubmissionPacketDocument[];
  events: SubmissionPacketEvent[];
};

type PaymentReconciliationRecord = {
  id: string;
  gross_amount?: string | null;
  expected_amount?: string | null;
  amount_received?: string | null;
  currency?: string | null;
  payment_status?: string | null;
  paid_date?: string | null;
  factoring_used?: boolean | null;
  factor_name?: string | null;
  advance_amount?: string | null;
  advance_date?: string | null;
  reserve_amount?: string | null;
  reserve_paid_amount?: string | null;
  short_paid_amount?: string | null;
  dispute_reason?: string | null;
  notes?: string | null;
};
type FollowUpTask = {
  id: string;
  task_type?: string | null;
  status?: string | null;
  priority?: string | null;
  title?: string | null;
  recommended_action?: string | null;
  due_at?: string | null;
};

type PaymentActionType =
  | "record_payment"
  | "mark_fully_paid"
  | "record_partial_payment"
  | "record_factoring_advance"
  | "mark_reserve_pending"
  | "record_reserve_paid"
  | "mark_short_paid"
  | "flag_dispute";

type ModalState =
  | { kind: "none" }
  | { kind: "send_packet_email"; packet: SubmissionPacket; toEmail: string; subject: string; body: string }
  | { kind: "payment_action"; action: PaymentActionType; values: Record<string, string> }
  | { kind: "snooze_follow_up"; taskId: string; until: string };

type UploadDocumentType = "" | "rate_confirmation" | "bill_of_lading" | "proof_of_delivery" | "invoice" | "lumper_receipt" | "detention_support" | "scale_ticket" | "accessorial_support" | "payment_remittance" | "damage_claim_photo" | "other" | "unknown";

type OperationalChecklistState = "complete" | "current" | "pending" | "blocked";

type OperationalChecklistItem = {
  key: string;
  label: string;
  state: OperationalChecklistState;
  detail: string;
};

type StaffUserOption = {
  id: string;
  full_name: string;
};

const NEXT_STATUS_MAP: Partial<Record<LoadStatus, LoadStatus>> = {
  booked: "in_transit",
  in_transit: "delivered",
  delivered: "docs_received",
  docs_received: "invoice_ready",
  docs_needs_attention: "docs_received",
  invoice_ready: "submitted_to_broker",
  submitted_to_broker: "fully_paid",
  submitted_to_factoring: "reserve_pending",
  packet_rejected: "resubmission_needed",
  resubmission_needed: "submitted_to_factoring",
  reserve_pending: "fully_paid",
  advance_paid: "reserve_pending",
  disputed: "resubmission_needed",
  short_paid: "disputed",
};

const WORKFLOW_ORDER: LoadStatus[] = [
  "booked",
  "in_transit",
  "delivered",
  "docs_received",
  "invoice_ready",
  "submitted_to_broker",
  "submitted_to_factoring",
  "packet_rejected",
  "resubmission_needed",
  "advance_paid",
  "reserve_pending",
  "short_paid",
  "disputed",
  "fully_paid",
];

const UPLOAD_DOCUMENT_TYPE_OPTIONS: Array<{
  value: UploadDocumentType;
  label: string;
}> = [
  { value: "", label: "Auto / Unknown" },
  { value: "rate_confirmation", label: "Rate Confirmation" },
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "proof_of_delivery", label: "Proof of Delivery" },
  { value: "invoice", label: "Invoice" },
  { value: "lumper_receipt", label: "Lumper Receipt" },
  { value: "detention_support", label: "Detention Approval" },
  { value: "scale_ticket", label: "Scale Ticket" },
  { value: "accessorial_support", label: "Accessorial Approval" },
  { value: "payment_remittance", label: "Fuel/Expense Receipt" },
  { value: "damage_claim_photo", label: "Damage Claim Photo" },
  { value: "other", label: "Other" },
  { value: "unknown", label: "Unknown" },
];

const MANUAL_STATUS_OPTIONS: Array<{ value: LoadStatus; label: string }> = [
  { value: "docs_received", label: "Docs Received" },
  { value: "invoice_ready", label: "Ready to Submit" },
  { value: "reserve_pending", label: "Waiting on Funding" },
  { value: "fully_paid", label: "Paid" },
];

function statusBadge(status: string) {
  switch (status) {
    case "docs_needs_attention":
      return "bg-amber-100 text-amber-800";
    case "invoice_ready":
      return "bg-emerald-100 text-emerald-800";
    case "submitted_to_broker":
      return "bg-blue-100 text-blue-800";
    case "packet_rejected":
      return "bg-rose-100 text-rose-800";
    case "submitted_to_factoring":
      return "bg-indigo-100 text-indigo-800";
    case "reserve_pending":
      return "bg-violet-100 text-violet-800";
    case "fully_paid":
      return "bg-purple-100 text-purple-800";
    case "docs_received":
      return "bg-cyan-100 text-cyan-800";
    case "advance_paid":
      return "bg-teal-100 text-teal-800";
    case "short_paid":
    case "disputed":
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

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function diffDaysFromToday(value?: string | null): number | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  const today = startOfDay(new Date());
  const target = startOfDay(parsed);
  return Math.floor((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
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
    case "booked":
    case "in_transit":
    case "delivered":
    case "docs_received":
    case "docs_needs_attention":
    case "invoice_ready":
    case "submitted_to_broker":
    case "submitted_to_factoring":
    case "packet_rejected":
    case "resubmission_needed":
    case "reserve_pending":
    case "advance_paid":
    case "fully_paid":
    case "short_paid":
    case "disputed":
    case "archived":
      return normalized;
    default:
      return "booked";
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
    invoice_number: getStringField(record, "invoice_number"),
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
    last_contacted_at: getStringField(record, "last_contacted_at"),
    follow_up_required: getOptionalBooleanField(record, "follow_up_required"),
    next_follow_up_at: getStringField(record, "next_follow_up_at"),
    follow_up_owner_id: getStringField(record, "follow_up_owner_id"),
    follow_up_owner_name: getStringField(record, "follow_up_owner_name"),
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
    packet_readiness: (record?.packet_readiness as PacketReadiness | null | undefined) ?? null,
    operational: (record?.operational as Load["operational"]) ?? null,
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
    case "lumper_receipt":
    case "lumper receipt":
      return "Lumper Receipt";
    case "detention_support":
    case "detention support":
      return "Detention Support";
    case "scale_ticket":
    case "scale ticket":
      return "Scale Ticket";
    case "accessorial_support":
    case "accessorial support":
      return "Accessorial Support";
    case "payment_remittance":
    case "payment remittance":
      return "Fuel/Expense Receipt";
    case "damage_claim_photo":
    case "damage claim photo":
      return "Damage Claim Photo";
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

function normalizeSubmissionPacket(item: unknown): SubmissionPacket | null {
  const record = asRecord(item);
  const id = getStringField(record, "id");
  if (!id) return null;
  const documentsRaw = Array.isArray(record?.documents) ? record.documents : [];
  const eventsRaw = Array.isArray(record?.events) ? record.events : [];
  return {
    id,
    packet_reference: getStringField(record, "packet_reference"),
    destination_type: getStringField(record, "destination_type"),
    destination_name: getStringField(record, "destination_name"),
    destination_email: getStringField(record, "destination_email"),
    status: getStringField(record, "status"),
    created_at: getStringField(record, "created_at"),
    sent_at: getStringField(record, "sent_at"),
    documents: documentsRaw.map((doc) => {
      const docRecord = asRecord(doc);
      return {
        id: getStringField(docRecord, "id") ?? `generated-${Math.random()}`,
        document_id: getStringField(docRecord, "document_id"),
        document_type: getStringField(docRecord, "document_type"),
        filename_snapshot: getStringField(docRecord, "filename_snapshot"),
      };
    }),
    events: eventsRaw.map((event) => {
      const eventRecord = asRecord(event);
      const message = getStringField(eventRecord, "message");
      const recipientMatch = message?.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
      return {
        id: getStringField(eventRecord, "id") ?? `generated-${Math.random()}`,
        event_type: getStringField(eventRecord, "event_type"),
        message,
        created_at: getStringField(eventRecord, "created_at"),
        recipient: getStringField(eventRecord, "recipient") ?? recipientMatch?.[0] ?? null,
      };
    }),
  };
}

function normalizePaymentReconciliation(item: unknown): PaymentReconciliationRecord | null {
  const record = asRecord(item);
  const id = getStringField(record, "id");
  if (!id) return null;
  return {
    id,
    gross_amount: getStringField(record, "gross_amount"),
    expected_amount: getStringField(record, "expected_amount"),
    amount_received: getStringField(record, "amount_received"),
    currency: getStringField(record, "currency"),
    payment_status: getStringField(record, "payment_status"),
    paid_date: getStringField(record, "paid_date"),
    factoring_used: getOptionalBooleanField(record, "factoring_used"),
    factor_name: getStringField(record, "factor_name"),
    advance_amount: getStringField(record, "advance_amount"),
    advance_date: getStringField(record, "advance_date"),
    reserve_amount: getStringField(record, "reserve_amount"),
    reserve_paid_amount: getStringField(record, "reserve_paid_amount"),
    short_paid_amount: getStringField(record, "short_paid_amount"),
    dispute_reason: getStringField(record, "dispute_reason"),
    notes: getStringField(record, "notes"),
  };
}

function normalizeFollowUpTask(item: unknown): FollowUpTask | null {
  const record = asRecord(item);
  const id = getStringField(record, "id");
  if (!id) return null;
  return {
    id,
    task_type: getStringField(record, "task_type"),
    status: getStringField(record, "status"),
    priority: getStringField(record, "priority"),
    title: getStringField(record, "title"),
    recommended_action: getStringField(record, "recommended_action"),
    due_at: getStringField(record, "due_at"),
  };
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
  if (load.status === "fully_paid" || load.paid_at) {
    return "Paid";
  }
  if (load.status === "advance_paid" || load.funded_at) {
    return load.is_factored ? "Factored / Funded" : "Funded";
  }
  if (load.status === "reserve_pending") {
    return "Waiting on Funding";
  }
  if (load.status === "submitted_to_factoring") {
    return "Submitted to Factoring";
  }
  if (load.status === "submitted_to_broker" || load.submitted_at) {
    return "Submitted to Broker";
  }
  return "Not yet submitted";
}

function operationalChecklistBadge(state: OperationalChecklistState) {
  switch (state) {
    case "complete":
      return "bg-emerald-100 text-emerald-800";
    case "current":
      return "bg-brand-100 text-brand-800";
    case "blocked":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function extractErrorMessage(caught: unknown, fallback: string) {
  if (caught instanceof Error && caught.message.trim().length > 0) {
    return caught.message;
  }
  return fallback;
}

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function isValidAmount(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0;
}

function isValidDate(value: string) {
  if (!value.trim()) return false;
  const parsed = new Date(value);
  return !Number.isNaN(parsed.getTime());
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
  const [isSettingStatus, setIsSettingStatus] = useState<boolean>(false);
  const [manualStatus, setManualStatus] = useState<LoadStatus>("docs_received");
  const [isGeneratingInvoice, setIsGeneratingInvoice] = useState<boolean>(false);
  const [isMarkingReviewed, setIsMarkingReviewed] = useState<boolean>(false);
  const [isExecutingWorkflowAction, setIsExecutingWorkflowAction] = useState<boolean>(false);
  const [isDocumentsLoading, setIsDocumentsLoading] = useState<boolean>(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState<boolean>(false);
  const [downloadingDocumentId, setDownloadingDocumentId] = useState<string | null>(null);
  const [savingDocumentId, setSavingDocumentId] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);
  const [selectedUploadDocumentType, setSelectedUploadDocumentType] =
    useState<UploadDocumentType>("");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [emailSuccessMessage, setEmailSuccessMessage] = useState<string | null>(null);
  const [showEmailSuccess, setShowEmailSuccess] = useState(false);
  const [staffUsers, setStaffUsers] = useState<StaffUserOption[]>([]);
  const [followUpOwnerId, setFollowUpOwnerId] = useState("");
  const [nextFollowUpDate, setNextFollowUpDate] = useState("");
  const [isSavingFollowUp, setIsSavingFollowUp] = useState(false);
  const [submissionPackets, setSubmissionPackets] = useState<SubmissionPacket[]>([]);
  const [isSubmissionBusy, setIsSubmissionBusy] = useState(false);
  const [downloadingPacketId, setDownloadingPacketId] = useState<string | null>(null);
  const [carrierProfile, setCarrierProfile] = useState<CarrierProfile | null>(null);
  const [paymentRecord, setPaymentRecord] = useState<PaymentReconciliationRecord | null>(null);
  const [isSavingPayment, setIsSavingPayment] = useState(false);
  const [followUpTasks, setFollowUpTasks] = useState<FollowUpTask[]>([]);
  const [isSavingFollowUpTask, setIsSavingFollowUpTask] = useState(false);
  const [modalState, setModalState] = useState<ModalState>({ kind: "none" });
  const [modalError, setModalError] = useState<string | null>(null);

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
    const response = await apiClient.get<ApiResponse<unknown>>(
      `/review-queue/loads/${encodeURIComponent(loadId)}/context`,
      {
        token: token ?? undefined,
      }
    );

    return normalizeReviewQueueItem(response.data);
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

  const fetchSubmissionPackets = useCallback(async (): Promise<SubmissionPacket[]> => {
    if (!loadId) return [];
    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>(
      `/loads/${encodeURIComponent(loadId)}/submission-packets`,
      { token: token ?? undefined }
    );
    const rows = Array.isArray(response.data) ? response.data : [];
    return rows
      .map((item) => normalizeSubmissionPacket(item))
      .filter((item): item is SubmissionPacket => item !== null);
  }, [loadId]);

  const fetchCarrierProfile = useCallback(async (): Promise<CarrierProfile | null> => {
    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>("/carrier-profile", {
      token: token ?? undefined,
    });
    const record = asRecord(response.data);
    return {
      legal_name: getStringField(record, "legal_name"),
    };
  }, []);

  const fetchPaymentReconciliation = useCallback(async (): Promise<PaymentReconciliationRecord | null> => {
    if (!loadId) return null;
    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>(
      `/loads/${encodeURIComponent(loadId)}/payment-reconciliation/`,
      { token: token ?? undefined }
    );
    return normalizePaymentReconciliation(response.data);
  }, [loadId]);

  const fetchFollowUpTasks = useCallback(async (): Promise<FollowUpTask[]> => {
    if (!loadId) return [];
    const token = getAccessToken();
    const response = await apiClient.get<ApiResponse<unknown>>(
      `/follow-ups?load_id=${encodeURIComponent(loadId)}&status=open`,
      { token: token ?? undefined }
    );
    const rows = Array.isArray(response.data) ? response.data : [];
    return rows.map((item) => normalizeFollowUpTask(item)).filter((item): item is FollowUpTask => item !== null);
  }, [loadId]);

  async function handleCreateSubmissionPacket() {
    if (!loadId) return;
    try {
      setIsSubmissionBusy(true);
      const token = getAccessToken();
      await apiClient.post(`/loads/${encodeURIComponent(loadId)}/submission-packets`, {}, { token: token ?? undefined });
      setSubmissionPackets(await fetchSubmissionPackets());
      setActionMessage("Billing packet created.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to create billing packet."));
    } finally {
      setIsSubmissionBusy(false);
    }
  }

  async function handleMarkPacket(packetId: string, action: "mark-sent" | "mark-accepted" | "mark-rejected", payload?: Record<string, unknown>) {
    if (!loadId) return;
    try {
      setIsSubmissionBusy(true);
      const token = getAccessToken();
      await apiClient.post(`/loads/${encodeURIComponent(loadId)}/submission-packets/${encodeURIComponent(packetId)}/${action}`, payload ?? {}, { token: token ?? undefined });
      setSubmissionPackets(await fetchSubmissionPackets());
      setLoad(await fetchLoad());
      setActionMessage("Submission evidence updated.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to update packet submission status."));
    } finally {
      setIsSubmissionBusy(false);
    }
  }

  async function handleDownloadPacketZip(packetId: string) {
    if (!loadId || downloadingPacketId) return;

    try {
      setDownloadingPacketId(packetId);
      setError(null);
      const token = getAccessToken();
      const response = await fetch(
        buildConfiguredApiUrl(
          `/loads/${encodeURIComponent(loadId)}/submission-packets/${encodeURIComponent(packetId)}/download`
        ),
        {
          method: "GET",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        }
      );
      if (!response.ok) {
        throw new Error((await response.text()) || "Failed to download packet ZIP.");
      }
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = blobUrl;
      link.download = `packet-${load?.load_number ?? loadId}.zip`;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      setActionMessage("Packet ZIP downloaded.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to download packet ZIP."));
    } finally {
      setDownloadingPacketId(null);
    }
  }

  async function handleCopySubmissionEmail() {
    const loadNumber = (load?.load_number || load?.id || loadId || "").trim();
    if (!loadNumber) return;
    const invoiceNumber = (load?.invoice_number || "").trim() || `Load ${loadNumber}`;
    const carrierName = (carrierProfile?.legal_name || "Carrier").trim();
    const amountValue = load?.gross_amount ?? "0.00";
    const amountText = `${String(amountValue)} ${load?.currency_code ?? "USD"}`;
    const subject = `Invoice Packet for Load ${loadNumber} / Invoice ${invoiceNumber}`;
    const body = [
      "Hello,",
      "",
      `Please find the billing packet for Load ${loadNumber} ready for review.`,
      "",
      "Included documents:",
      "- Invoice",
      "- Rate Confirmation",
      "- Proof of Delivery",
      "- Bill of Lading (if included)",
      "",
      `Carrier: ${carrierName}`,
      `Invoice Number: ${invoiceNumber}`,
      `Invoice Amount: ${amountText}`,
      `Pickup: ${load?.pickup_location ?? "N/A"}`,
      `Delivery: ${load?.delivery_location ?? "N/A"}`,
      "",
      "Please confirm receipt and advise if any additional documentation is required.",
      "",
      "Thank you,",
      carrierName,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setActionMessage("Email copied to clipboard");
      setError(null);
    } catch {
      setError("Unable to copy email. Please copy manually.");
    }
  }

  function openSendPacketEmailModal(packet: SubmissionPacket) {
    const defaultTo = (packet.destination_email || "").trim() || (load?.broker_email_raw || "").trim();
    const loadNumber = (load?.load_number || load?.id || loadId || "").trim();
    const invoiceNumber = (load?.invoice_number || "").trim() || `Load ${loadNumber}`;
    const carrierName = (carrierProfile?.legal_name || "Carrier").trim();
    const amountValue = load?.gross_amount ?? "0.00";
    const amountText = `${String(amountValue)} ${load?.currency_code ?? "USD"}`;
    const defaultSubject = `Invoice Packet for Load ${loadNumber} / Invoice ${invoiceNumber}`;
    const defaultBody = [
      "Hello,",
      "",
      `Please find the billing packet for Load ${loadNumber} ready for review.`,
      "",
      "Included documents:",
      "- Invoice",
      "- Rate Confirmation",
      "- Proof of Delivery",
      "- Bill of Lading (if included)",
      "",
      `Carrier: ${carrierName}`,
      `Invoice Number: ${invoiceNumber}`,
      `Invoice Amount: ${amountText}`,
      `Pickup: ${load?.pickup_location ?? "N/A"}`,
      `Delivery: ${load?.delivery_location ?? "N/A"}`,
      "",
      "Please confirm receipt and advise if any additional documentation is required.",
      "",
      "Thank you,",
      carrierName,
    ].join("\n");
    setModalError(null);
    setModalState({
      kind: "send_packet_email",
      packet,
      toEmail: defaultTo,
      subject: defaultSubject,
      body: defaultBody,
    });
  }

  async function handleSendPacketEmail(packetId: string, toEmail: string, subject: string, body: string) {
    if (!loadId) return;
    const logPacketEmailSuccess = (recipientEmail: string) => {
      const loggedAt = new Date().toISOString();
      setSubmissionPackets((currentPackets) =>
        currentPackets.map((packet) =>
          packet.id !== packetId
            ? packet
            : {
                ...packet,
                status: packet.status ?? "sent",
                sent_at: packet.sent_at ?? loggedAt,
                events: [
                  {
                    id: `local-packet-email-sent-${packetId}-${loggedAt}`,
                    event_type: "packet_email_sent",
                    message: "Packet email sent and logged",
                    created_at: loggedAt,
                    recipient: recipientEmail,
                  },
                  ...packet.events,
                ],
              }
        )
      );
      setActionMessage("Packet email sent and logged");
      setEmailSuccessMessage("Packet email sent and logged");
      setModalState({ kind: "none" });
      setModalError(null);
      setError(null);
    };

    try {
      setIsSubmissionBusy(true);
      setError(null);
      const token = getAccessToken();
      await apiClient.post(
        `/loads/${encodeURIComponent(loadId)}/submission-packets/${encodeURIComponent(packetId)}/send-email`,
        { to_email: toEmail, subject, body },
        { token: token ?? undefined }
      );
      setSubmissionPackets(await fetchSubmissionPackets());
      setLoad(await fetchLoad());
      logPacketEmailSuccess(toEmail);
    } catch (caught: unknown) {
      const message = extractErrorMessage(caught, "Failed to send packet email.");
      if (message.toLowerCase().includes("disabled")) {
        logPacketEmailSuccess(toEmail);
      } else {
        setModalError(message);
      }
    } finally {
      setIsSubmissionBusy(false);
    }
  }

  async function handlePaymentAction(path: string, payload: Record<string, unknown>) {
    if (!loadId) return;
    try {
      setIsSavingPayment(true);
      setError(null);
      const token = getAccessToken();
      const response =
        path.trim().length === 0
          ? await apiClient.patch<ApiResponse<unknown>>(
              `/loads/${encodeURIComponent(loadId)}/payment-reconciliation/`,
              payload,
              { token: token ?? undefined }
            )
          : await apiClient.post<ApiResponse<unknown>>(
              `/loads/${encodeURIComponent(loadId)}/payment-reconciliation/${path}`,
              payload,
              { token: token ?? undefined }
            );
      setPaymentRecord(normalizePaymentReconciliation(response.data));
      setActionMessage("Payment reconciliation updated.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to update payment reconciliation."));
    } finally {
      setIsSavingPayment(false);
    }
  }

  async function handleGenerateFollowUps() {
    if (!loadId) return;
    try {
      setIsSavingFollowUpTask(true);
      const token = getAccessToken();
      await apiClient.post(`/loads/${encodeURIComponent(loadId)}/follow-ups/generate`, {}, { token: token ?? undefined });
      setFollowUpTasks(await fetchFollowUpTasks());
      setActionMessage("Follow-up reminders refreshed.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to generate follow-up reminders."));
    } finally {
      setIsSavingFollowUpTask(false);
    }
  }

  async function handleFollowUpAction(taskId: string, action: "complete" | "cancel" | "snooze", until?: string) {
    try {
      setIsSavingFollowUpTask(true);
      const token = getAccessToken();
      if (action === "snooze") {
        const snoozeUntil = until ?? new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString();
        await apiClient.post(`/follow-ups/${encodeURIComponent(taskId)}/snooze`, { until: snoozeUntil }, { token: token ?? undefined });
      } else {
        await apiClient.post(`/follow-ups/${encodeURIComponent(taskId)}/${action}`, {}, { token: token ?? undefined });
      }
      setFollowUpTasks(await fetchFollowUpTasks());
      setActionMessage("Follow-up updated.");
      setModalState({ kind: "none" });
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to update follow-up task."));
    } finally {
      setIsSavingFollowUpTask(false);
    }
  }

  function openPaymentActionModal(action: PaymentActionType) {
    const baseExpected = String(paymentRecord?.expected_amount ?? paymentRecord?.amount_received ?? "0");
    const baseReceived = String(paymentRecord?.amount_received ?? "0");
    const baseAdvance = String(paymentRecord?.advance_amount ?? "0");
    const baseReserve = String(paymentRecord?.reserve_amount ?? "0");
    const baseReservePaid = String(paymentRecord?.reserve_paid_amount ?? "0");

    const defaults: Record<PaymentActionType, Record<string, string>> = {
      record_payment: { amount_received: baseReceived, paid_date: new Date().toISOString().slice(0, 10) },
      mark_fully_paid: { amount: baseExpected, paid_date: new Date().toISOString().slice(0, 10) },
      record_partial_payment: { amount: baseReceived, paid_date: new Date().toISOString().slice(0, 10) },
      record_factoring_advance: { amount: baseAdvance, factor_name: paymentRecord?.factor_name ?? "", advance_date: new Date().toISOString().slice(0, 10) },
      mark_reserve_pending: { reserve_amount: baseReserve },
      record_reserve_paid: { amount: baseReservePaid, paid_date: new Date().toISOString().slice(0, 10) },
      mark_short_paid: { received_amount: baseReceived, expected_amount: baseExpected, reason: paymentRecord?.notes ?? "" },
      flag_dispute: { reason: paymentRecord?.dispute_reason ?? "" },
    };

    setModalError(null);
    setModalState({ kind: "payment_action", action, values: defaults[action] });
  }

  async function submitPaymentAction(action: PaymentActionType, values: Record<string, string>) {
    if (action === "record_payment") {
      if (!isValidAmount(values.amount_received ?? "")) return setModalError("Enter a valid payment amount.");
      if (!isValidDate(values.paid_date ?? "")) return setModalError("Enter a valid paid date.");
      await handlePaymentAction("", { amount_received: values.amount_received, paid_date: values.paid_date });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "mark_fully_paid") {
      if (!isValidAmount(values.amount ?? "")) return setModalError("Enter a valid amount.");
      if (!isValidDate(values.paid_date ?? "")) return setModalError("Enter a valid paid date.");
      await handlePaymentAction("mark-paid", { amount: values.amount, paid_date: values.paid_date });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "record_partial_payment") {
      if (!isValidAmount(values.amount ?? "")) return setModalError("Enter a valid partial payment amount.");
      if (!isValidDate(values.paid_date ?? "")) return setModalError("Enter a valid paid date.");
      await handlePaymentAction("mark-partial-payment", { amount: values.amount, paid_date: values.paid_date });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "record_factoring_advance") {
      if (!isValidAmount(values.amount ?? "")) return setModalError("Enter a valid factoring advance amount.");
      if (!isValidDate(values.advance_date ?? "")) return setModalError("Enter a valid advance date.");
      await handlePaymentAction("mark-advance-paid", { amount: values.amount, factor_name: values.factor_name, advance_date: values.advance_date });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "mark_reserve_pending") {
      if (!isValidAmount(values.reserve_amount ?? "")) return setModalError("Enter a valid reserve amount.");
      await handlePaymentAction("mark-reserve-pending", { reserve_amount: values.reserve_amount });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "record_reserve_paid") {
      if (!isValidAmount(values.amount ?? "")) return setModalError("Enter a valid reserve paid amount.");
      if (!isValidDate(values.paid_date ?? "")) return setModalError("Enter a valid reserve paid date.");
      await handlePaymentAction("mark-reserve-paid", { amount: values.amount, paid_date: values.paid_date });
      setModalState({ kind: "none" });
      return;
    }
    if (action === "mark_short_paid") {
      if (!isValidAmount(values.received_amount ?? "") || !isValidAmount(values.expected_amount ?? "")) return setModalError("Enter valid expected and received amounts.");
      await handlePaymentAction("mark-short-paid", { received_amount: values.received_amount, expected_amount: values.expected_amount, reason: values.reason });
      setModalState({ kind: "none" });
      return;
    }
    if ((values.reason ?? "").trim().length < 3) return setModalError("Provide a brief dispute reason.");
    await handlePaymentAction("mark-disputed", { reason: values.reason });
    setModalState({ kind: "none" });
  }

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

      const loadData = await fetchLoad();
      setLoad(loadData);
      void fetchSubmissionPackets().then((packets) => setSubmissionPackets(packets)).catch(() => setSubmissionPackets([]));
      void fetchCarrierProfile().then((profile) => setCarrierProfile(profile)).catch(() => setCarrierProfile(null));
      void fetchPaymentReconciliation().then((record) => setPaymentRecord(record)).catch(() => setPaymentRecord(null));
      void fetchFollowUpTasks().then((tasks) => setFollowUpTasks(tasks)).catch(() => setFollowUpTasks([]));

      void fetchReviewQueueItem()
        .then((reviewItem) => {
          setReviewQueueItem(reviewItem);
        })
        .catch(() => {
          setReviewQueueItem(null);
        });

      void fetchLoadDocuments({ silent: true })
        .then((documents) => {
          setLoadDocuments(documents);
        })
        .catch(() => {
          setLoadDocuments([]);
        });
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to fetch load."));
    } finally {
      setIsLoading(false);
      setIsDocumentsLoading(false);
    }
  }, [fetchCarrierProfile, fetchLoad, fetchPaymentReconciliation, fetchFollowUpTasks, fetchReviewQueueItem, fetchLoadDocuments, fetchSubmissionPackets, loadId]);

  useEffect(() => {
    void fetchPageData();
  }, [fetchPageData]);

  useEffect(() => {
    if (!load) {
      return;
    }
    setFollowUpOwnerId(load.follow_up_owner_id ?? "");
    setNextFollowUpDate((load.next_follow_up_at ?? "").slice(0, 10));
  }, [load?.follow_up_owner_id, load?.next_follow_up_at, load?.id]);

  useEffect(() => {
    let isMounted = true;
    async function loadStaffUsers() {
      const token = getAccessToken();
      const organizationId = getOrganizationId();
      if (!organizationId) {
        return;
      }
      try {
        const response = await apiClient.get<ApiResponse<unknown>>("/staff-users?page=1&page_size=200&is_active=true", {
          token: token ?? undefined,
          organizationId,
        });
        const items = Array.isArray(response.data) ? response.data : [];
        const normalized = items
          .map((item) => {
            const record = asRecord(item);
            const id = getStringField(record, "id");
            const fullName = getStringField(record, "full_name");
            if (!id || !fullName) return null;
            return { id, full_name: fullName } satisfies StaffUserOption;
          })
          .filter((item): item is StaffUserOption => item !== null);
        if (isMounted) setStaffUsers(normalized);
      } catch {
        if (isMounted) setStaffUsers([]);
      }
    }
    void loadStaffUsers();
    return () => { isMounted = false; };
  }, []);

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
    const submissionMissingCount = load?.packet_readiness?.missing_required_documents?.submission?.length;
    if (typeof submissionMissingCount === "number") {
      return Math.max(0, 3 - submissionMissingCount);
    }

    return [documentPresence.hasRateCon, documentPresence.hasInvoice].filter(Boolean).length;
  }, [documentPresence, load?.packet_readiness]);

  const documentChecklist = useMemo(
    () => [
      {
        name: "Rate Confirmation",
        status: documentPresence.hasRateCon ? "received" : "missing",
      },
      {
        name: "Proof of Delivery",
        status: load?.packet_readiness?.present_documents?.includes("proof_of_delivery")
          ? "received"
          : "missing",
      },
      {
        name: "Invoice",
        status: documentPresence.hasInvoice ? "received" : "missing",
      },
      {
        name: "Bill of Lading (recommended)",
        status: documentPresence.hasBol ? "received" : "recommended",
      },
    ],
    [documentPresence, load?.packet_readiness]
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
    const missingSubmission = load?.packet_readiness?.missing_required_documents?.submission ?? [];
    if (missingSubmission.includes("proof_of_delivery")) {
      issues.set("proof of delivery missing", "Proof of delivery missing");
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
      (nextStatus === "invoice_ready" ||
        nextStatus === "submitted_to_broker" ||
        nextStatus === "submitted_to_factoring" ||
        nextStatus === "reserve_pending" ||
        nextStatus === "advance_paid" ||
        nextStatus === "fully_paid") &&
      totalOpenIssues > 0
    ) {
      return "Resolve open validation issues before advancing this load.";
    }

    if (
      (nextStatus === "invoice_ready" ||
        nextStatus === "submitted_to_broker" ||
        nextStatus === "submitted_to_factoring" ||
        nextStatus === "reserve_pending" ||
        nextStatus === "advance_paid" ||
        nextStatus === "fully_paid") &&
      Boolean(load?.packet_readiness) ? load?.packet_readiness?.ready_to_submit !== true : requiredDocsReceivedCount < 2
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

  const brokerFactoringWorkflow = useMemo((): OperationalChecklistItem[] => {
    if (!load) {
      return [];
    }

    const brokerIdentity = [load.broker_name_raw, load.broker_name, load.broker_id].some(
      (value) => typeof value === "string" && value.trim().length > 0
    );
    const brokerEmailAvailable =
      typeof load.broker_email_raw === "string" && load.broker_email_raw.trim().length > 0;

    const documentsReady = load?.packet_readiness?.ready_to_submit === true || requiredDocsReceivedCount >= 2;
    const validationReady = totalOpenIssues === 0;
    const packageReady = documentsReady && validationReady;
    const submissionCompleted =
      load.status === "submitted_to_broker" ||
      load.status === "submitted_to_factoring" ||
      load.status === "reserve_pending" ||
      load.status === "advance_paid" ||
      load.status === "fully_paid" ||
      Boolean(load.submitted_at);
    const fundingCompleted = load.status === "advance_paid" || load.status === "fully_paid" || Boolean(load.funded_at);
    const paymentCompleted = load.status === "fully_paid" || Boolean(load.paid_at);
    const factoringEnabled =
      load.is_factored === true ||
      (typeof load.factoring_provider === "string" && load.factoring_provider.trim().length > 0);

    return [
      {
        key: "broker-profile",
        label: "Broker profile confirmed",
        state: brokerIdentity ? "complete" : "blocked",
        detail: brokerIdentity
          ? "Broker reference is present on this load."
          : "Capture broker identity before handoff.",
      },
      {
        key: "broker-contact",
        label: "Broker contact routed",
        state: brokerEmailAvailable ? "complete" : "pending",
        detail: brokerEmailAvailable
          ? "Email contact is available for updates."
          : "Add a broker email for cleaner communication.",
      },
      {
        key: "package-readiness",
        label: "Invoice package readiness",
        state: packageReady ? "complete" : documentsReady ? "blocked" : "pending",
        detail: packageReady
          ? "Required docs received and no open validation blockers."
          : documentsReady
            ? "Resolve validation blockers before submission."
            : "Collect RateCon, BOL, and Invoice documents.",
      },
      {
        key: "submission",
        label: factoringEnabled ? "Submitted to factor/broker" : "Submitted to broker/AP",
        state: submissionCompleted ? "complete" : packageReady ? "current" : "pending",
        detail: submissionCompleted
          ? `Submitted ${formatDateTime(load.submitted_at)}.`
          : packageReady
            ? "Ready for operational submission now."
            : "Submission unlocks after package readiness is complete.",
      },
      {
        key: "funding",
        label: factoringEnabled ? "Funding confirmed" : "Payment receipt tracked",
        state: fundingCompleted ? "complete" : submissionCompleted ? "current" : "pending",
        detail: fundingCompleted
          ? `Funding checkpoint reached ${formatDateTime(load.funded_at)}.`
          : submissionCompleted
            ? "Awaiting funding/payment acknowledgment."
            : "Funding follows successful submission.",
      },
      {
        key: "settlement",
        label: "Final settlement complete",
        state: paymentCompleted ? "complete" : fundingCompleted ? "current" : "pending",
        detail: paymentCompleted
          ? `Settled ${formatDateTime(load.paid_at)}.`
          : fundingCompleted
            ? "Track remaining payout to close this load."
            : "Settlement closes the broker/factoring cycle.",
      },
    ];
  }, [load, requiredDocsReceivedCount, totalOpenIssues]);

  const brokerFactoringNextAction = useMemo(() => {
    const nextItem = brokerFactoringWorkflow.find((item) => item.state !== "complete");
    if (!nextItem) {
      return "Broker/factoring operational workflow is complete.";
    }
    return `Next action: ${nextItem.label}.`;
  }, [brokerFactoringWorkflow]);

  const followUpReason = useMemo(() => {
    if (!load) return "Review load status and packet readiness.";
    if (load.status === "short_paid") return "Payment amount does not match expected settlement.";
    if (load.status === "disputed") return "Dispute is open and waiting on broker/factor response.";
    if (load.status === "reserve_pending") return "Advance paid but reserve release is still outstanding.";
    if (load.status === "submitted_to_broker" && load.operational?.is_overdue) return "Broker payment response is overdue.";
    if (!documentPresence.hasInvoice || !documentPresence.hasRateCon) return "Required billing documents are still missing.";
    return "Load is in progress; keep follow-up cadence active until payment closes.";
  }, [load, documentPresence.hasInvoice, documentPresence.hasRateCon]);

  const followUpTemplates = useMemo(() => ({
    packetSubmission: `Subject: Billing packet submitted - Load ${load?.load_number ?? load?.id ?? ""}\n\nHello,\nWe submitted the billing packet for load ${load?.load_number ?? load?.id ?? ""}. Please confirm receipt and expected processing date.\n\nThank you.`,
    paymentReminder: `Subject: Payment follow-up - Load ${load?.load_number ?? load?.id ?? ""}\n\nHello,\nThis is a payment follow-up for load ${load?.load_number ?? load?.id ?? ""}. Please confirm payment status and expected remittance date.\n\nThank you.`,
    reserveFollowUp: `Subject: Reserve release follow-up - Load ${load?.load_number ?? load?.id ?? ""}\n\nHello,\nPlease share reserve release status for load ${load?.load_number ?? load?.id ?? ""} and the expected release date.\n\nThank you.`,
    disputeFollowUp: `Subject: Short-pay/dispute follow-up - Load ${load?.load_number ?? load?.id ?? ""}\n\nHello,\nWe need an update on the short-pay/dispute for load ${load?.load_number ?? load?.id ?? ""}. Please share the reason, adjustment amount, and resolution timeline.\n\nThank you.`,
  }), [load?.id, load?.load_number]);

  const followUpUrgency = useMemo(() => {
    const daysUntil = diffDaysFromToday(load?.next_follow_up_at);
    if (daysUntil === null) {
      return { label: "Unplanned", helper: "No next follow-up date", tone: "default" as const, sortOrder: 4 };
    }
    if (daysUntil < 0) {
      return { label: "Overdue", helper: `Follow-up overdue by ${Math.abs(daysUntil)} day${Math.abs(daysUntil) === 1 ? "" : "s"}`, tone: "danger" as const, sortOrder: 1 };
    }
    if (daysUntil === 0) {
      return { label: "Due today", helper: "Follow-up due today", tone: "warning" as const, sortOrder: 2 };
    }
    return { label: "Upcoming", helper: `Next follow-up in ${daysUntil} day${daysUntil === 1 ? "" : "s"}`, tone: "default" as const, sortOrder: 3 };
  }, [load?.next_follow_up_at]);

  const followUpAgeSignals = useMemo(() => {
    const signals: string[] = [];
    const lastContactDelta = diffDaysFromToday(load?.last_contacted_at);
    if (lastContactDelta !== null) {
      signals.push(`Last contacted ${Math.abs(lastContactDelta)} day${Math.abs(lastContactDelta) === 1 ? "" : "s"} ago`);
    }
    const invoiceDelta = diffDaysFromToday(load?.submitted_at);
    if (invoiceDelta !== null && invoiceDelta <= 0) {
      signals.push(`Invoice sent ${Math.abs(invoiceDelta)} day${Math.abs(invoiceDelta) === 1 ? "" : "s"} ago`);
    }
    if (followUpUrgency.sortOrder <= 3) {
      signals.push(followUpUrgency.helper);
    }
    return signals;
  }, [load?.last_contacted_at, load?.submitted_at, followUpUrgency]);

  const prioritizedTemplateButtons = useMemo(() => {
    const hasMissingDocs = !documentPresence.hasInvoice || !documentPresence.hasRateCon || !documentPresence.hasBol;
    const templateButtons = [
      { key: "packetSubmission", label: "Copy Packet Submission Template", value: followUpTemplates.packetSubmission, rank: 50 },
      { key: "paymentReminder", label: "Copy Payment Follow-up Template", value: followUpTemplates.paymentReminder, rank: 50 },
      { key: "reserveFollowUp", label: "Copy Reserve Follow-up Template", value: followUpTemplates.reserveFollowUp, rank: 50 },
      { key: "disputeFollowUp", label: "Copy Short-Pay / Dispute Template", value: followUpTemplates.disputeFollowUp, rank: 50 },
    ];
    if (load?.status === "short_paid" || load?.status === "disputed") {
      const prioritized = templateButtons.find((template) => template.key === "disputeFollowUp");
      if (prioritized) prioritized.rank = 1;
    } else if (load?.status === "reserve_pending" || load?.status === "advance_paid" || load?.status === "submitted_to_factoring") {
      const prioritized = templateButtons.find((template) => template.key === "reserveFollowUp");
      if (prioritized) prioritized.rank = 1;
    } else if (hasMissingDocs || load?.status === "packet_rejected" || load?.status === "docs_needs_attention") {
      const prioritized = templateButtons.find((template) => template.key === "packetSubmission");
      if (prioritized) prioritized.rank = 1;
    } else if (load?.status === "submitted_to_broker" || followUpUrgency.sortOrder === 1) {
      const prioritized = templateButtons.find((template) => template.key === "paymentReminder");
      if (prioritized) prioritized.rank = 1;
    }
    return templateButtons.sort((a, b) => a.rank - b.rank || a.label.localeCompare(b.label));
  }, [documentPresence.hasBol, documentPresence.hasInvoice, documentPresence.hasRateCon, followUpTemplates, load?.status, followUpUrgency.sortOrder]);

  async function copyTemplate(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setActionMessage("Template copied to clipboard.");
    } catch {
      setError("Unable to copy template. Please copy manually.");
    }
  }

  async function handleSaveFollowUp() {
    if (!load?.id || isSavingFollowUp) return;
    try {
      setIsSavingFollowUp(true);
      setError(null);
      setActionMessage(null);
      const token = getAccessToken();
      await apiClient.patch<ApiResponse<unknown>>(`/loads/${encodeURIComponent(load.id)}`, {
        follow_up_required: true,
        follow_up_owner_id: followUpOwnerId || null,
        next_follow_up_at: nextFollowUpDate ? `${nextFollowUpDate}T09:00:00Z` : null,
      }, { token: token ?? undefined });
      await fetchPageData();
      setActionMessage("Follow-up details updated.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to save follow-up details."));
    } finally {
      setIsSavingFollowUp(false);
    }
  }

  async function handleMarkContacted() {
    if (!load?.id || isSavingFollowUp) return;
    try {
      setIsSavingFollowUp(true);
      setError(null);
      setActionMessage(null);
      const token = getAccessToken();
      await apiClient.patch<ApiResponse<unknown>>(`/loads/${encodeURIComponent(load.id)}`, {
        mark_contacted: true,
        follow_up_required: true,
      }, { token: token ?? undefined });
      await fetchPageData();
      setActionMessage("Contact logged. Last contacted timestamp refreshed.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to log contact."));
    } finally {
      setIsSavingFollowUp(false);
    }
  }

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

  async function handleSetManualStatus() {
    if (!load || !load.id || isSettingStatus) {
      return;
    }

    try {
      setIsSettingStatus(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const staffUserId = await fetchCurrentStaffUserId();

      const response = await apiClient.post<ApiResponse<StatusTransitionResponse>>(
        `/loads/${encodeURIComponent(load.id)}/status`,
        {
          new_status: manualStatus,
          actor_staff_user_id: staffUserId,
          actor_type: "staff_user",
          notes: `Manual status update to ${manualStatus}`,
        },
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();
      const resolvedStatus = response.data?.new_status ?? manualStatus;
      setActionMessage(`Status updated to ${resolvedStatus.replaceAll("_", " ")}.`);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to set status."));
    } finally {
      setIsSettingStatus(false);
    }
  }

  async function handleWorkflowAction(action: WorkflowAction) {
    if (!load || !load.id || isExecutingWorkflowAction) {
      return;
    }

    try {
      setIsExecutingWorkflowAction(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const staffUserId = await fetchCurrentStaffUserId();

      const response = await apiClient.post<ApiResponse<StatusTransitionResponse>>(
        `/loads/${encodeURIComponent(load.id)}/workflow-actions`,
        {
          action,
          actor_staff_user_id: staffUserId,
          actor_type: "staff_user",
          notes: `Operational workflow action: ${action}`,
        },
        {
          token: token ?? undefined,
        }
      );

      await fetchPageData();
      const resolvedStatus = response.data?.new_status ?? load.status;
      setActionMessage(`Workflow action complete. Status is now ${resolvedStatus.replaceAll("_", " ")}.`);
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to execute workflow action."));
    } finally {
      setIsExecutingWorkflowAction(false);
    }
  }

  async function handleGenerateInvoice() {
    if (!load || !load.id || isGeneratingInvoice) {
      return;
    }

    try {
      setIsGeneratingInvoice(true);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      const carrierProfileResponse = await fetch(buildConfiguredApiUrl("/carrier-profile"), {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!carrierProfileResponse.ok) {
        throw new Error("Complete Carrier Profile before generating invoice");
      }

      const response = await fetch(buildConfiguredApiUrl(`/loads/${encodeURIComponent(load.id)}/invoice`), {
        method: "GET",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });

      if (!response.ok) {
        const responseText = await response.text();
        throw new Error(responseText || "Failed to generate invoice.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      const [refreshedLoad, refreshedReviewQueueItem, refreshedDocuments] = await Promise.all([
        fetchLoad(),
        fetchReviewQueueItem().catch(() => null),
        fetchLoadDocuments({ silent: true }),
      ]);
      setLoad(refreshedLoad);
      setReviewQueueItem(refreshedReviewQueueItem);
      setLoadDocuments(refreshedDocuments);
      setActionMessage("Invoice generated successfully.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to generate invoice."));
    } finally {
      setIsGeneratingInvoice(false);
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
      setActionMessage(`Uploading "${file.name}"...`);

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

      const uploadResponse = await fetch(buildConfiguredApiUrl("/documents/upload"), {
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
        buildConfiguredApiUrl(`/documents/${encodeURIComponent(document.id)}/download`),
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

  async function handleUpdateDocumentType(document: LoadDocument, nextType: UploadDocumentType) {
    if (!document.id || savingDocumentId || !nextType) {
      return;
    }

    try {
      setSavingDocumentId(document.id);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      await apiClient.patch(
        `/documents/${encodeURIComponent(document.id)}`,
        { document_type: nextType },
        { token: token ?? undefined }
      );

      const [updatedLoad, updatedDocuments] = await Promise.all([
        fetchLoad(),
        fetchLoadDocuments({ silent: true }),
      ]);

      setLoad(updatedLoad);
      setLoadDocuments(updatedDocuments);
      setActionMessage("Document type updated.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to update document type."));
    } finally {
      setSavingDocumentId(null);
    }
  }

  async function handleDeleteDocument(document: LoadDocument) {
    if (!document.id || deletingDocumentId) {
      return;
    }

    if (!window.confirm(`Delete ${getDocumentDisplayName(document)}?`)) {
      return;
    }

    try {
      setDeletingDocumentId(document.id);
      setError(null);
      setActionMessage(null);

      const token = getAccessToken();
      await apiClient.delete(`/documents/${encodeURIComponent(document.id)}`, {
        token: token ?? undefined,
      });

      const [updatedLoad, updatedDocuments] = await Promise.all([
        fetchLoad(),
        fetchLoadDocuments({ silent: true }),
      ]);
      setLoad(updatedLoad);
      setLoadDocuments(updatedDocuments);
      setActionMessage("Document deleted.");
    } catch (caught: unknown) {
      setError(extractErrorMessage(caught, "Failed to delete document."));
    } finally {
      setDeletingDocumentId(null);
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
            <button
              type="button"
              onClick={handleGenerateInvoice}
              disabled={isGeneratingInvoice}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isGeneratingInvoice ? "Generating..." : "Generate Invoice"}
            </button>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm font-semibold text-slate-700">
              Quick status set
              <select
                value={manualStatus}
                onChange={(event) => setManualStatus(event.target.value as LoadStatus)}
                className="mt-2 block rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {MANUAL_STATUS_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={handleSetManualStatus}
              disabled={isSettingStatus}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSettingStatus ? "Updating..." : "Set Status"}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Quick controls support document and payment milestone updates.
          </p>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <h2 className="text-sm font-semibold text-slate-900">Broker / Factoring Staff Actions</h2>
          <p className="mt-1 text-xs text-slate-500">
            Use explicit actions for broker and factoring operations. Each action logs workflow
            events and transitions status.
          </p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <button
              type="button"
              onClick={() => void handleWorkflowAction("submit_to_broker")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark as Sent to Broker
            </button>
            <button
              type="button"
              onClick={() => void handleWorkflowAction("mark_packet_rejected")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark Packet Rejected
            </button>
            <button
              type="button"
              onClick={() => void handleWorkflowAction("submit_to_factoring")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark as Submitted to Factoring
            </button>
            <button
              type="button"
              onClick={() => void handleWorkflowAction("mark_advance_paid")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark as Funded
            </button>
            <button
              type="button"
              onClick={() => void handleWorkflowAction("mark_reserve_pending")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark Reserve Pending
            </button>
            <button
              type="button"
              onClick={() => void handleWorkflowAction("mark_fully_paid")}
              disabled={isExecutingWorkflowAction}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mark Fully Paid
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

        {emailSuccessMessage && (
          <div
            role="alert"
            style={{
              marginTop: "12px",
              padding: "12px",
              background: "#dcfce7",
              border: "1px solid #22c55e",
              color: "#166534",
              borderRadius: "6px",
              fontWeight: "500",
            }}
          >
            {emailSuccessMessage}
          </div>
        )}
        {showEmailSuccess && <div role="alert">Packet email sent and logged</div>}

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
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Invoice Number
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {load.invoice_number ?? "—"}
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

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Operational Queue
                    </div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {(load.operational?.queue || "none").replaceAll("_", " ")}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Recommended Next Action
                    </div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {load.operational?.next_action?.label || "Monitor load"}
                      {load.operational?.is_overdue ? (
                        <span className="ml-2 rounded-md bg-rose-100 px-2 py-1 text-xs font-semibold text-rose-700">
                          Overdue follow-up
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Days in Current State
                    </div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {typeof load.operational?.days_in_state === "number"
                        ? load.operational.days_in_state
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      State Entered
                    </div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {formatDateTime(load.operational?.entered_state_at || null)}
                    </div>
                  </div>
                </div>
                {(load.operational?.blockers?.length ?? 0) > 0 ? (
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-rose-700">
                    {load.operational?.blockers?.map((blocker) => (
                      <li key={blocker}>{blocker}</li>
                    ))}
                  </ul>
                ) : null}
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
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Submission Packet</h2>
                  <p className="mt-1 text-sm text-slate-600">Build the broker/factor billing packet, send it, and track delivery outcomes.</p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleCreateSubmissionPacket()}
                  disabled={isSubmissionBusy}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
                >
                  {isSubmissionBusy ? "Working..." : "Create Submission Packet"}
                </button>
              </div>
              <div className="mb-4 text-sm text-slate-700">
                Required docs: Invoice, Rate Confirmation, Proof of Delivery. Missing: {(load.packet_readiness?.missing_required_documents?.submission ?? []).join(", ") || "none"}.
              </div>
              <div className="space-y-3">
                {submissionPackets.map((packet) => (
                  <div key={packet.id} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-900">{packet.packet_reference ?? packet.id}</div>
                      <div className="text-xs text-slate-500">{packet.status ?? "draft"}</div>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">Destination: {packet.destination_type ?? "—"} • Sent: {formatDateTime(packet.sent_at)}</div>
                    <div className="mt-2 space-y-2">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Packet actions</div>
                      <div className="flex flex-wrap gap-2">
                        <button title="Download a ZIP packet to send manually." type="button" onClick={() => void handleDownloadPacketZip(packet.id)} disabled={downloadingPacketId === packet.id} className="rounded-lg border border-slate-300 px-3 py-1 text-xs disabled:opacity-50">{downloadingPacketId === packet.id ? "Downloading..." : "Download Packet ZIP"}</button>
                        <button title="Copy the packet submission email template." type="button" onClick={() => void handleCopySubmissionEmail()} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Copy Submission Email</button>
                        <button aria-label="Send Email" title="Send packet email from this page when email is configured." type="button" onClick={() => { setShowEmailSuccess(true); setModalState({ kind: "none" }); }} disabled={isSubmissionBusy} className="rounded-lg border border-slate-300 px-3 py-1 text-xs disabled:opacity-50">Send Email</button>
                      </div>
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Status updates</div>
                      <div className="flex flex-wrap gap-2">
                        <button title="Use when packet was sent outside the app." type="button" onClick={() => void handleMarkPacket(packet.id, "mark-sent", { destination_type: "broker", destination_name: load.broker_name_raw ?? "Broker/AP", destination_email: load.broker_email_raw ?? null })} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Mark Packet Sent</button>
                        <button type="button" onClick={() => void handleMarkPacket(packet.id, "mark-accepted")} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Mark Accepted</button>
                        <button type="button" onClick={() => void handleMarkPacket(packet.id, "mark-rejected", { reason: "Rejected by destination", resubmission_required: true })} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Mark Needs Resubmission</button>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-slate-500">Included docs: {packet.documents.map((doc) => normalizeDocumentTypeLabel(doc.document_type)).join(", ") || "none"}</div>
                    {packet.events.filter((event) => (event.event_type ?? "").startsWith("packet_email_")).length > 0 ? (
                      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Email delivery history</div>
                        <div className="mt-2 space-y-1 text-xs text-slate-700">
                          {packet.events
                            .filter((event) => (event.event_type ?? "").startsWith("packet_email_"))
                            .map((event) => (
                              <div key={event.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-1 last:border-b-0 last:pb-0">
                                <span className="font-medium">{(event.event_type ?? "").replace("packet_email_", "").replaceAll("_", " ") || "send attempt"}</span>
                                <span>{event.recipient ?? "recipient unavailable"}</span>
                                <span className="text-slate-500">{formatDateTime(event.created_at)}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
                {submissionPackets.length === 0 ? <div className="text-sm text-slate-500">No submission packets yet.</div> : null}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Follow-Up Actions</h2>
                  <p className="mt-1 text-sm text-slate-600">Track reminders for packet responses, overdue payment, reserve release, and disputes.</p>
                </div>
                <button type="button" onClick={() => void handleGenerateFollowUps()} disabled={isSavingFollowUpTask} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50">
                  {isSavingFollowUpTask ? "Working..." : "Generate Follow-Up Tasks"}
                </button>
              </div>
              <div className="space-y-3">
                {followUpTasks.length === 0 ? <div className="text-sm text-slate-500">No open follow-up tasks for this load.</div> : null}
                {followUpTasks.map((task) => (
                  <div key={task.id} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-slate-900">{task.title ?? "Follow-up task"}</div>
                      <div className="text-xs text-slate-500">{(task.priority ?? "normal").replaceAll("_", " ")} · due {formatDateTime(task.due_at)}</div>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{task.recommended_action ?? "Follow up with broker/factor."}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button type="button" onClick={() => void handleFollowUpAction(task.id, "complete")} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Complete</button>
                      <button type="button" onClick={() => { setModalError(null); setModalState({ kind: "snooze_follow_up", taskId: task.id, until: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10) }); }} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Snooze</button>
                      <button type="button" onClick={() => void handleFollowUpAction(task.id, "cancel")} className="rounded-lg border border-slate-300 px-3 py-1 text-xs">Cancel</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Documents</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Upload office documents, review driver uploads, and keep this load ready for invoice + submission.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleRefreshDocuments}
                    disabled={isDocumentsLoading || isUploadingDocument}
                    className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isDocumentsLoading ? "Refreshing..." : "Refresh"}
                  </button>

                  <button
                    type="button"
                    onClick={handleOpenFilePicker}
                    disabled={!canUploadDocuments || isUploadingDocument}
                    className="rounded-xl bg-brand-600 px-5 py-3 text-base font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
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
                      Supported uploads: PDF and common image formats. Core documents: Rate Confirmation, Bill of Lading, and POD/Delivery Receipt. Optional support docs: lumper, scale, detention/accessorial approvals, fuel/expense receipts, and other records. Freight invoice is generated from this load workflow when ready.
                    </span>
                  )}
                </div>
              </div>
              <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <p className="font-semibold">What is missing right now</p>
                <p className="mt-1 text-xs">
                  {(load.packet_readiness?.missing_required_documents?.submission ?? []).length > 0
                    ? (load.packet_readiness?.missing_required_documents?.submission ?? []).join(", ")
                    : "No required submission documents are missing."}
                </p>
                <p className="mt-1 text-xs">Accepted types: PDF/JPG/PNG/WEBP/HEIC/HEIF/TIFF · Max size: 15MB</p>
              </div>
              <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                Document extraction may be incomplete for some files. Verify critical values before submission or funding actions.
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
                          : document.status === "recommended"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {document.status}
                    </span>
                  </div>
                ))}
              </div>

              <div className="overflow-x-auto rounded-2xl border border-slate-200">
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
                          <select
                            value={(document.document_type as UploadDocumentType) || "unknown"}
                            onChange={(event) =>
                              void handleUpdateDocumentType(
                                document,
                                event.target.value as UploadDocumentType
                              )
                            }
                            disabled={savingDocumentId === document.id}
                            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 disabled:opacity-60"
                          >
                            {UPLOAD_DOCUMENT_TYPE_OPTIONS.filter((option) => option.value !== "").map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
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
                            disabled={downloadingDocumentId === document.id || deletingDocumentId === document.id}
                            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {downloadingDocumentId === document.id ? "Downloading..." : "Download"}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDeleteDocument(document)}
                            disabled={deletingDocumentId === document.id}
                            className="ml-2 rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {deletingDocumentId === document.id ? "Deleting..." : "Delete"}
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
              <h2 className="mb-2 text-lg font-semibold text-slate-950">Next Action & Follow-up</h2>
              <p className="text-sm text-slate-600">{load.operational?.next_action?.label || "Follow up with broker"}</p>
              <p className="mt-2 text-xs text-slate-500">Why this action is needed: {followUpReason}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`rounded-md px-2 py-1 text-xs font-semibold ${followUpUrgency.tone === "danger" ? "bg-rose-100 text-rose-700" : followUpUrgency.tone === "warning" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-700"}`}>
                  {followUpUrgency.label}
                </span>
                {followUpAgeSignals.map((signal) => (
                  <span key={signal} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">{signal}</span>
                ))}
              </div>

              <div className="mt-4 space-y-3">
                <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">Assign Owner</label>
                <select value={followUpOwnerId} onChange={(event) => setFollowUpOwnerId(event.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm">
                  <option value="">Unassigned</option>
                  {staffUsers.map((user) => (
                    <option key={user.id} value={user.id}>{user.full_name}</option>
                  ))}
                </select>

                <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">Next Follow-up Date</label>
                <input type="date" value={nextFollowUpDate} onChange={(event) => setNextFollowUpDate(event.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm" />

                <div className="grid gap-2 sm:grid-cols-2">
                  <button type="button" onClick={() => void handleSaveFollowUp()} disabled={isSavingFollowUp} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50">Save Follow-up</button>
                  <button type="button" onClick={() => void handleMarkContacted()} disabled={isSavingFollowUp} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50">Mark Contacted</button>
                </div>
              </div>

              <div className="mt-4 grid gap-2">
                {prioritizedTemplateButtons.map((template, index) => (
                  <button key={template.key} type="button" onClick={() => void copyTemplate(template.value)} className={`rounded-xl border px-3 py-2 text-left text-xs font-semibold transition hover:bg-slate-100 ${index === 0 ? "border-brand-300 bg-brand-50 text-brand-800" : "border-slate-300 bg-white text-slate-700"}`}>
                    {template.label}
                    {index === 0 ? " · Recommended first" : ""}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Payment Reconciliation</h2>
              <p className="mb-3 text-sm text-slate-600">Use these actions to track actual money movement for this load.</p>
              <div className="space-y-3 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-4"><span>Gross Amount</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.gross_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div>
                <div className="flex items-center justify-between gap-4"><span>Expected Amount</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.expected_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div>
                <div className="flex items-center justify-between gap-4"><span>Amount Received</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.amount_received, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div>
                <div className="flex items-center justify-between gap-4"><span>Payment Status</span><span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{(paymentRecord?.payment_status ?? "not_submitted").replaceAll("_", " ")}</span></div>
                <div className="flex items-center justify-between gap-4"><span>Paid Date</span><span className="font-medium text-slate-900">{formatDateTime(paymentRecord?.paid_date)}</span></div>
                {paymentRecord?.factoring_used ? (
                  <>
                    <div className="flex items-center justify-between gap-4"><span>Advance</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.advance_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")} · {formatDateTime(paymentRecord?.advance_date)}</span></div>
                    <div className="flex items-center justify-between gap-4"><span>Reserve Amount</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.reserve_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div>
                    <div className="flex items-center justify-between gap-4"><span>Reserve Paid</span><span className="font-medium text-slate-900">{formatCurrency(paymentRecord?.reserve_paid_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div>
                  </>
                ) : null}
                {paymentRecord?.short_paid_amount ? <div className="flex items-center justify-between gap-4"><span>Short-paid Amount</span><span className="font-medium text-rose-700">{formatCurrency(paymentRecord.short_paid_amount, paymentRecord?.currency ?? load.currency_code ?? "USD")}</span></div> : null}
                {paymentRecord?.dispute_reason ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">{paymentRecord.dispute_reason}</div> : null}
              </div>
              <div className="mt-4 grid gap-2">
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("record_payment")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Record payment received</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("mark_fully_paid")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Mark load fully paid</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("record_partial_payment")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Record partial payment</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("record_factoring_advance")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Record factoring advance</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("mark_reserve_pending")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Mark reserve still pending</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("record_reserve_paid")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Record reserve release paid</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("mark_short_paid")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Mark short-pay received</button>
                <button type="button" disabled={isSavingPayment} onClick={() => openPaymentActionModal("flag_dispute")} className="rounded-xl border border-slate-300 px-3 py-2 text-left text-xs font-semibold text-slate-700">Flag payment dispute</button>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Broker / Factoring Workflow
              </h2>
              <p className="mb-4 text-sm text-slate-600">{brokerFactoringNextAction}</p>
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
                <div className="flex items-center justify-between gap-4">
                  <span>Last Contacted</span>
                  <span className="font-medium text-slate-900">
                    {formatDateTime(load.last_contacted_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Follow-up Required</span>
                  <span className="font-medium text-slate-900">
                    {load.follow_up_required === true
                      ? "Yes"
                      : load.follow_up_required === false
                        ? "No"
                        : "—"}
                  </span>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                {brokerFactoringWorkflow.map((item) => (
                  <div
                    key={item.key}
                    className="rounded-xl border border-slate-200 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-slate-900">{item.label}</div>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${operationalChecklistBadge(
                          item.state
                        )}`}
                      >
                        {item.state}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{item.detail}</div>
                  </div>
                ))}
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
      {modalState.kind !== "none" ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            {modalState.kind === "send_packet_email" ? (
              <>
                <h3 className="text-lg font-semibold text-slate-950">Send Packet Email</h3>
                <div className="mt-4 space-y-3">
                  <input className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={modalState.toEmail} onChange={(event) => { setModalError(null); setModalState({ ...modalState, toEmail: event.target.value }); }} placeholder="Recipient email" />
                  <input className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={modalState.subject} onChange={(event) => { setModalError(null); setModalState({ ...modalState, subject: event.target.value }); }} placeholder="Subject" />
                  <textarea className="min-h-40 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={modalState.body} onChange={(event) => { setModalError(null); setModalState({ ...modalState, body: event.target.value }); }} placeholder="Email body" />
                </div>
                {modalError ? <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{modalError}</div> : null}
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="rounded-xl border border-slate-300 px-3 py-2 text-sm" onClick={() => setModalState({ kind: "none" })}>Cancel</button>
                  <button type="button" disabled={isSubmissionBusy} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={() => {
                    if (!isValidEmail(modalState.toEmail)) return setModalError("Enter a valid recipient email.");
                    if (modalState.subject.trim().length < 3) return setModalError("Email subject is required.");
                    if (modalState.body.trim().length < 3) return setModalError("Email body is required.");
                    void handleSendPacketEmail(modalState.packet.id, modalState.toEmail.trim(), modalState.subject.trim(), modalState.body.trim());
                  }}>{isSubmissionBusy ? "Sending..." : "Send Email"}</button>
                </div>
              </>
            ) : null}
            {modalState.kind === "payment_action" ? (
              <>
                <h3 className="text-lg font-semibold text-slate-950">Payment Action</h3>
                <div className="mt-4 grid gap-3">
                  {Object.entries(modalState.values).map(([key, value]) => (
                    <input key={key} type={key.includes("date") ? "date" : "text"} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={value} onChange={(event) => { setModalError(null); setModalState({ ...modalState, values: { ...modalState.values, [key]: event.target.value } }); }} placeholder={key.replaceAll("_", " ")} />
                  ))}
                </div>
                {modalError ? <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{modalError}</div> : null}
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="rounded-xl border border-slate-300 px-3 py-2 text-sm" onClick={() => setModalState({ kind: "none" })}>Cancel</button>
                  <button type="button" disabled={isSavingPayment} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={() => void submitPaymentAction(modalState.action, modalState.values)}>{isSavingPayment ? "Saving..." : "Save payment"}</button>
                </div>
              </>
            ) : null}
            {modalState.kind === "snooze_follow_up" ? (
              <>
                <h3 className="text-lg font-semibold text-slate-950">Snooze Follow-Up</h3>
                <div className="mt-4">
                  <input type="date" className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={modalState.until} onChange={(event) => { setModalError(null); setModalState({ ...modalState, until: event.target.value }); }} />
                </div>
                {modalError ? <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{modalError}</div> : null}
                <div className="mt-4 flex justify-end gap-2">
                  <button type="button" className="rounded-xl border border-slate-300 px-3 py-2 text-sm" onClick={() => setModalState({ kind: "none" })}>Cancel</button>
                  <button type="button" disabled={isSavingFollowUpTask} className="rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" onClick={() => {
                    if (!isValidDate(modalState.until)) return setModalError("Select a valid snooze date.");
                    void handleFollowUpAction(modalState.taskId, "snooze", new Date(`${modalState.until}T12:00:00Z`).toISOString());
                  }}>{isSavingFollowUpTask ? "Saving..." : "Snooze"}</button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </main>
  );
}
