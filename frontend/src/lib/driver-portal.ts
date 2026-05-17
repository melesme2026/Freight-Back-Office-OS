import { canonicalDocumentType, documentTypeLabel } from "@/lib/document-types";

export type DriverWorkflowStepKey =
  | "assigned"
  | "picked_up"
  | "in_transit"
  | "delivered"
  | "docs_uploaded"
  | "docs_approved"
  | "invoice_ready"
  | "paid";

export type DriverDocumentStatus = "missing" | "uploaded" | "under_review" | "approved" | "rejected" | "needs_reupload";

export type DriverChecklistItem = {
  type: string;
  label: string;
  required: boolean;
  status: DriverDocumentStatus;
  helper: string;
};

export type DriverNextAction = {
  title: string;
  description: string;
  tone: "action" | "waiting" | "success" | "blocked";
  ctaLabel: string;
};

export const DRIVER_REQUIRED_DOCUMENTS = ["rate_confirmation", "bill_of_lading", "proof_of_delivery"] as const;

export const DRIVER_OPTIONAL_DOCUMENTS = [
  "lumper_receipt",
  "scale_ticket",
  "fuel_receipt",
  "accessorial_support",
  "other",
] as const;

export const DRIVER_WORKFLOW_STEPS: { key: DriverWorkflowStepKey; label: string }[] = [
  { key: "assigned", label: "Assigned" },
  { key: "picked_up", label: "Picked Up" },
  { key: "in_transit", label: "In Transit" },
  { key: "delivered", label: "Delivered" },
  { key: "docs_uploaded", label: "Docs Uploaded" },
  { key: "docs_approved", label: "Docs Approved" },
  { key: "invoice_ready", label: "Invoice Ready" },
  { key: "paid", label: "Paid" },
];

export function toDriverStatus(rawStatus: string | null | undefined, hasMissingDocs: boolean): string {
  const normalized = (rawStatus ?? "").trim().toLowerCase();

  if (hasMissingDocs && ["delivered", "docs_received", "invoice_ready"].includes(normalized)) {
    return "paperwork needed";
  }

  if (["booked", "assigned"].includes(normalized)) return "assigned";
  if (["picked_up"].includes(normalized)) return "picked up";
  if (["in_transit"].includes(normalized)) return "in transit";
  if (["delivered"].includes(normalized)) return hasMissingDocs ? "docs needed" : "delivered";
  if (["docs_received"].includes(normalized)) return "under review";
  if (["invoice_ready"].includes(normalized)) return "invoice ready";
  if (["submitted_to_broker", "submitted_to_factoring"].includes(normalized)) return "submitted";
  if (["fully_paid", "paid"].includes(normalized)) return "paid";
  return hasMissingDocs ? "docs needed" : "in transit";
}

export function labelForDocumentType(documentType: string): string {
  const map: Record<string, string> = {
    rate_confirmation: "Rate Confirmation",
    bill_of_lading: "BOL",
    proof_of_delivery: "Proof of Delivery",
    lumper_receipt: "Lumper Receipt",
    scale_ticket: "Scale Ticket",
    fuel_receipt: "Fuel Receipt",
    accessorial_support: "Accessorial",
    detention_support: "Detention Support",
    other: "Other Supporting Docs",
  };

  return map[canonicalDocumentType(documentType)] ?? map[documentType] ?? documentTypeLabel(documentType);
}

export function documentStatusFromProcessingStatus(status?: string | null): DriverDocumentStatus {
  const normalized = (status ?? "").trim().toLowerCase();
  if (["approved", "validated", "accepted", "completed", "complete"].includes(normalized)) return "approved";
  if (["rejected", "failed", "invalid"].includes(normalized)) return "rejected";
  if (["needs_reupload", "reupload_requested", "requires_reupload"].includes(normalized)) return "needs_reupload";
  if (["processing", "pending", "queued", "uploaded", "submitted", "received"].includes(normalized)) return "under_review";
  return "uploaded";
}

export function statusLabel(status: DriverDocumentStatus): string {
  return {
    missing: "Missing",
    uploaded: "Uploaded",
    under_review: "Under Review",
    approved: "Approved",
    rejected: "Rejected",
    needs_reupload: "Needs Reupload",
  }[status];
}

export function statusClasses(status: DriverDocumentStatus): string {
  return {
    missing: "border-amber-200 bg-amber-50 text-amber-800",
    uploaded: "border-sky-200 bg-sky-50 text-sky-800",
    under_review: "border-violet-200 bg-violet-50 text-violet-800",
    approved: "border-emerald-200 bg-emerald-50 text-emerald-800",
    rejected: "border-rose-200 bg-rose-50 text-rose-800",
    needs_reupload: "border-orange-200 bg-orange-50 text-orange-800",
  }[status];
}

export function checklistFromReadiness(
  readiness: Record<string, unknown> | null | undefined,
  documentStatuses: Record<string, DriverDocumentStatus> = {},
): DriverChecklistItem[] {
  const present = Array.isArray(readiness?.present_documents)
    ? readiness.present_documents.filter((item): item is string => typeof item === "string").map(canonicalDocumentType)
    : [];
  const presentSet = new Set(present);

  const build = (type: string, required: boolean): DriverChecklistItem => {
    const canonical = canonicalDocumentType(type);
    const status = documentStatuses[canonical] ?? (presentSet.has(canonical) ? "under_review" : "missing");
    const label = labelForDocumentType(canonical);
    return {
      type: canonical,
      label,
      required,
      status,
      helper: required
        ? status === "missing"
          ? `${label} is required before accounting can finish the packet.`
          : `${label} is on file for this load.`
        : status === "missing"
          ? `${label} is optional, but upload it if it supports reimbursement or billing.`
          : `${label} was added as supporting paperwork.`,
    };
  };

  return [
    ...DRIVER_REQUIRED_DOCUMENTS.map((type) => build(type, true)),
    ...DRIVER_OPTIONAL_DOCUMENTS.map((type) => build(type, false)),
  ];
}

export function getMissingRequiredDocuments(checklist: DriverChecklistItem[]): DriverChecklistItem[] {
  return checklist.filter((item) => item.required && ["missing", "rejected", "needs_reupload"].includes(item.status));
}

export function documentCompletion(checklist: DriverChecklistItem[]): { completed: number; total: number; percent: number } {
  const required = checklist.filter((item) => item.required);
  const completed = required.filter((item) => !["missing", "rejected", "needs_reupload"].includes(item.status)).length;
  return { completed, total: required.length, percent: required.length === 0 ? 100 : Math.round((completed / required.length) * 100) };
}

export function nextActionForLoad(params: {
  rawStatus?: string | null;
  checklist: DriverChecklistItem[];
  hasRejectedDocument?: boolean;
}): DriverNextAction {
  const rawStatus = (params.rawStatus ?? "").toLowerCase();
  const missing = getMissingRequiredDocuments(params.checklist);
  const rejected = params.checklist.find((item) => item.status === "rejected" || item.status === "needs_reupload");

  if (rejected || params.hasRejectedDocument) {
    return {
      title: `Reupload ${rejected?.label ?? "requested document"}`,
      description: "The back office needs a cleaner copy before the packet can move forward.",
      tone: "blocked",
      ctaLabel: "Upload replacement",
    };
  }
  if (missing.length > 0) {
    return {
      title: `Upload ${missing[0].label}`,
      description: missing.length === 1 ? "This is the last required document for paperwork review." : `${missing.length} required documents are still needed for this packet.`,
      tone: "action",
      ctaLabel: "Upload documents",
    };
  }
  if (["docs_received", "delivered"].includes(rawStatus)) {
    return {
      title: "Dispatcher reviewing documents",
      description: "All required paperwork is submitted. Dispatch or accounting will reach out only if something needs attention.",
      tone: "waiting",
      ctaLabel: "Review packet",
    };
  }
  if (["invoice_ready", "submitted_to_broker", "submitted_to_factoring"].includes(rawStatus)) {
    return {
      title: "Packet approved",
      description: "Paperwork is accepted and the back office is moving the invoice/payment workflow forward.",
      tone: "success",
      ctaLabel: "View status",
    };
  }
  if (["fully_paid", "paid"].includes(rawStatus)) {
    return {
      title: "Load complete",
      description: "No action needed. This load is closed from the driver paperwork side.",
      tone: "success",
      ctaLabel: "View documents",
    };
  }
  return {
    title: "Keep load status current",
    description: "Send an in-transit update or mark delivered when the freight is complete.",
    tone: "waiting",
    ctaLabel: "Open load",
  };
}

export function workflowStepState(rawStatus?: string | null, checklist: DriverChecklistItem[] = []): Record<DriverWorkflowStepKey, "done" | "current" | "upcoming"> {
  const status = (rawStatus ?? "").toLowerCase();
  const missing = getMissingRequiredDocuments(checklist).length > 0;
  let currentIndex = 0;
  if (["picked_up"].includes(status)) currentIndex = 1;
  if (["in_transit"].includes(status)) currentIndex = 2;
  if (["delivered"].includes(status)) currentIndex = 3;
  if (["docs_received"].includes(status) || (status === "delivered" && !missing)) currentIndex = 4;
  if (["invoice_ready"].includes(status)) currentIndex = 6;
  if (["submitted_to_broker", "submitted_to_factoring"].includes(status)) currentIndex = 6;
  if (["fully_paid", "paid"].includes(status)) currentIndex = 7;

  return DRIVER_WORKFLOW_STEPS.reduce<Record<DriverWorkflowStepKey, "done" | "current" | "upcoming">>((acc, step, index) => {
    acc[step.key] = index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming";
    return acc;
  }, {} as Record<DriverWorkflowStepKey, "done" | "current" | "upcoming">);
}
