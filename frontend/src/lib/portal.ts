import { apiClient } from "@/lib/api-client";

const PORTAL_TOKEN_KEY = "fbos_portal_access_token";

export type PortalDocument = {
  id: string;
  document_type: string | null;
  original_filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  processing_status: string | null;
  received_at: string | null;
  download_allowed: boolean;
};

export type PortalPacket = {
  id: string;
  packet_reference: string | null;
  status: string | null;
  sent_at: string | null;
  accepted_at: string | null;
  rejected_at: string | null;
  documents: Array<{ document_type: string | null; filename_snapshot: string | null }>;
};

export type PortalLoad = {
  id: string;
  load_number: string | null;
  status: string | null;
  pickup_date: string | null;
  delivery_date: string | null;
  pickup_location: string | null;
  delivery_location: string | null;
  broker_name: string | null;
  customer_account_name: string | null;
  rate_confirmation_number: string | null;
  bol_number: string | null;
  invoice_number: string | null;
  documents_complete: boolean;
  has_ratecon: boolean;
  has_bol: boolean;
  has_invoice: boolean;
  packet_readiness?: {
    ready?: boolean;
    ready_to_submit?: boolean;
    missing_documents?: string[];
    present_documents?: string[];
    required_documents?: string[] | { invoice?: string[]; submission?: string[] };
    missing_required_documents?: { invoice?: string[]; submission?: string[] };
  };
  submitted_at: string | null;
  paid_at: string | null;
  updated_at: string | null;
};

export type PortalScope = {
  load_id: string;
  role: string;
  contact_email: string;
  contact_name?: string | null;
  allow_packet_download?: boolean;
  allow_document_upload?: boolean;
};

type ApiEnvelope<T> = { data: T; meta?: Record<string, unknown>; error?: unknown };

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getPortalToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(PORTAL_TOKEN_KEY);
}

export function setPortalToken(token: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(PORTAL_TOKEN_KEY, token.trim());
}

export function clearPortalToken(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(PORTAL_TOKEN_KEY);
}

function portalOptions(token?: string, timeoutMs = 15_000) {
  return {
    token: token ?? getPortalToken() ?? undefined,
    authMode: "auto" as const,
    onUnauthorized: "throw" as const,
    timeoutMs,
  };
}

export async function fetchPortalScope(token?: string): Promise<{ scope: PortalScope; load: PortalLoad }> {
  const response = await apiClient.get<ApiEnvelope<{ scope: PortalScope; load: PortalLoad }>>("/portal/me", portalOptions(token, 10_000));
  return response.data;
}

export async function fetchPortalLoad(loadId: string, token?: string): Promise<{ load: PortalLoad; documents: PortalDocument[]; packets: PortalPacket[] }> {
  const response = await apiClient.get<ApiEnvelope<{ load: PortalLoad; documents: PortalDocument[]; packets: PortalPacket[] }>>(`/portal/loads/${loadId}`, portalOptions(token, 10_000));
  return response.data;
}

export async function uploadPortalDocument(loadId: string, documentType: string, file: File, token?: string): Promise<PortalDocument> {
  const form = new FormData();
  form.append("document_type", documentType);
  form.append("file", file);
  const response = await apiClient.post<ApiEnvelope<PortalDocument>>(`/portal/loads/${loadId}/documents/upload`, form, portalOptions(token, 10_000));
  return response.data;
}

export async function downloadPortalPacket(loadId: string, packetId: string, token?: string): Promise<Blob> {
  return apiClient.getBlob(`/portal/loads/${loadId}/packets/${packetId}/download`, portalOptions(token, 10_000));
}

export async function downloadPortalDocument(loadId: string, documentId: string, token?: string): Promise<Blob> {
  return apiClient.getBlob(`/portal/loads/${loadId}/documents/${documentId}/download`, portalOptions(token, 10_000));
}

export function validatePortalUploadFile(file: File): string | null {
  const allowed = ["application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif", "image/tiff"];
  const maxBytes = 25 * 1024 * 1024;
  if (!allowed.includes(file.type)) return "Upload a PDF or supported image file.";
  if (file.size > maxBytes) return "File is too large. Upload a file under 25 MB.";
  return null;
}
