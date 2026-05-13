import { buildApiUrl } from "@/lib/config";
import { getAccessToken, getOrganizationId, getTokenType } from "@/lib/auth";

export type QueuedDriverUpload = {
  id: string;
  loadId: string | null;
  documentType: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  dataUrl: string;
  queuedAt: string;
  attempts: number;
  lastError: string | null;
};

export type DriverUploadProgress = {
  loaded: number;
  total: number;
  percent: number;
};

const DRIVER_UPLOAD_QUEUE_KEY = "adwa.driver.uploadQueue.v1";
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
const MAX_QUEUE_ITEMS = 12;
const MAX_RETRY_ATTEMPTS = 5;
export class DriverUploadNetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DriverUploadNetworkError";
  }
}

const ALLOWED_UPLOAD_MIME_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/jpg",
  "image/heic",
  "image/heif",
  "image/tiff",
]);

function hasBrowserStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readQueue(): QueuedDriverUpload[] {
  if (!hasBrowserStorage()) return [];

  const raw = window.localStorage.getItem(DRIVER_UPLOAD_QUEUE_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isQueuedDriverUpload);
  } catch {
    return [];
  }
}

function writeQueue(queue: QueuedDriverUpload[]): void {
  if (!hasBrowserStorage()) return;
  window.localStorage.setItem(DRIVER_UPLOAD_QUEUE_KEY, JSON.stringify(queue.slice(0, MAX_QUEUE_ITEMS)));
  window.dispatchEvent(new CustomEvent("driver-upload-queue-changed"));
}

function isQueuedDriverUpload(value: unknown): value is QueuedDriverUpload {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    (typeof item.loadId === "string" || item.loadId === null) &&
    typeof item.documentType === "string" &&
    typeof item.fileName === "string" &&
    typeof item.fileType === "string" &&
    typeof item.fileSize === "number" &&
    typeof item.dataUrl === "string" &&
    typeof item.queuedAt === "string" &&
    typeof item.attempts === "number" &&
    (typeof item.lastError === "string" || item.lastError === null)
  );
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read file for offline queue."));
    reader.readAsDataURL(file);
  });
}

function dataUrlToFile(dataUrl: string, fileName: string, fileType: string): File {
  const [metadata, base64] = dataUrl.split(",");
  const mime = metadata.match(/data:(.*?);base64/)?.[1] || fileType || "application/octet-stream";
  const binary = window.atob(base64 ?? "");
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return new File([bytes], fileName, { type: mime });
}

function safeUploadSuccessFallback(request: XMLHttpRequest): Record<string, unknown> {
  return {
    data: [],
    status: request.status,
    ok: true,
  };
}

function parseXhrResponseBody(request: XMLHttpRequest, fallback?: unknown): unknown {
  const contentType = request.getResponseHeader("content-type") ?? "";
  const body = request.responseText;
  if (!body) return fallback ?? body;
  if (!contentType.toLowerCase().includes("application/json")) return body;

  try {
    return JSON.parse(body) as unknown;
  } catch {
    return fallback ?? body;
  }
}

function formatXhrNetworkError(request: XMLHttpRequest, uploadUrl: string): DriverUploadNetworkError {
  const responseUrl = request.responseURL || uploadUrl;
  const detail = [
    `url=${responseUrl}`,
    `status=${request.status}`,
    request.statusText ? `statusText=${request.statusText}` : null,
  ]
    .filter(Boolean)
    .join(" ");

  return new DriverUploadNetworkError(
    `Network upload failed (${detail}). The document can be queued and retried when online.`
  );
}

function uploadViaXhr(
  formData: FormData,
  onProgress?: (progress: DriverUploadProgress) => void
): Promise<unknown> {
  const token = getAccessToken();
  const tokenType = getTokenType();
  const organizationId = getOrganizationId();
  const uploadUrl = buildApiUrl("/driver/documents/upload");

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    let settled = false;
    const resolveOnce = (value: unknown) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };
    const rejectOnce = (error: Error) => {
      if (settled) return;
      settled = true;
      reject(error);
    };

    request.open("POST", uploadUrl);
    request.setRequestHeader("Accept", "application/json");
    if (token) request.setRequestHeader("Authorization", `${tokenType} ${token}`);
    if (organizationId) request.setRequestHeader("X-Organization-Id", organizationId);

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      onProgress?.({
        loaded: event.loaded,
        total: event.total,
        percent: Math.min(100, Math.round((event.loaded / event.total) * 100)),
      });
    };

    request.onload = () => {
      try {
        const isSuccess = request.status >= 200 && request.status < 300;
        const parsedBody = parseXhrResponseBody(
          request,
          isSuccess ? safeUploadSuccessFallback(request) : undefined
        );
        if (isSuccess) {
          resolveOnce(parsedBody);
          return;
        }
        const message = extractUploadErrorMessage(parsedBody) || `Upload failed (${request.status}).`;
        rejectOnce(new Error(message));
      } catch (error: unknown) {
        rejectOnce(error instanceof Error ? error : new Error("Upload response could not be processed."));
      }
    };

    request.onerror = () => rejectOnce(formatXhrNetworkError(request, uploadUrl));
    request.onabort = () => rejectOnce(new Error("Upload was canceled before it finished."));
    request.send(formData);
  });
}

function extractUploadErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return typeof payload === "string" ? payload : null;
  const record = payload as Record<string, unknown>;
  const detail = record.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const detailRecord = detail as Record<string, unknown>;
    if (typeof detailRecord.message === "string") return detailRecord.message;
    if (typeof detailRecord.code === "string") return detailRecord.code;
  }
  const error = record.error;
  if (error && typeof error === "object" && !Array.isArray(error)) {
    const errorRecord = error as Record<string, unknown>;
    if (typeof errorRecord.message === "string") return errorRecord.message;
  }
  return typeof record.message === "string" ? record.message : null;
}

export function getDriverUploadQueue(): QueuedDriverUpload[] {
  return readQueue();
}

export function subscribeToDriverUploadQueue(listener: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = () => listener();
  window.addEventListener("driver-upload-queue-changed", handler);
  window.addEventListener("storage", handler);
  window.addEventListener("online", handler);
  return () => {
    window.removeEventListener("driver-upload-queue-changed", handler);
    window.removeEventListener("storage", handler);
    window.removeEventListener("online", handler);
  };
}

export function validateDriverUploadFile(file: File): string | null {
  if (!ALLOWED_UPLOAD_MIME_TYPES.has(file.type)) {
    return "Upload error: only PDF or image files are allowed.";
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return "Upload error: file exceeds 15MB limit.";
  }
  return null;
}

export function buildDriverUploadFormData(input: {
  organizationId: string;
  documentType: string;
  file: File;
  loadId?: string | null;
  replace?: boolean;
}): FormData {
  const formData = new FormData();
  formData.append("organization_id", input.organizationId);
  formData.append("document_type", input.documentType);
  formData.append("file", input.file);
  if (input.loadId) formData.append("load_id", input.loadId);
  if (input.replace) formData.append("replace", "true");
  return formData;
}

export async function uploadDriverDocumentWithProgress(input: {
  organizationId: string;
  documentType: string;
  file: File;
  loadId?: string | null;
  replace?: boolean;
  onProgress?: (progress: DriverUploadProgress) => void;
}): Promise<unknown> {
  const formData = buildDriverUploadFormData(input);
  return uploadViaXhr(formData, input.onProgress);
}

export async function enqueueDriverUpload(input: {
  file: File;
  documentType: string;
  loadId?: string | null;
}): Promise<QueuedDriverUpload> {
  const queue = readQueue();
  if (queue.length >= MAX_QUEUE_ITEMS) {
    throw new Error("Offline queue is full. Reconnect and sync existing uploads before adding more.");
  }

  const item: QueuedDriverUpload = {
    id: crypto.randomUUID(),
    loadId: input.loadId ?? null,
    documentType: input.documentType,
    fileName: input.file.name,
    fileType: input.file.type,
    fileSize: input.file.size,
    dataUrl: await fileToDataUrl(input.file),
    queuedAt: new Date().toISOString(),
    attempts: 0,
    lastError: null,
  };
  writeQueue([item, ...queue]);
  return item;
}

export function removeQueuedDriverUpload(id: string): void {
  writeQueue(readQueue().filter((item) => item.id !== id));
}

export async function processDriverUploadQueue(options: {
  organizationId: string;
  onProgress?: (item: QueuedDriverUpload, progress: DriverUploadProgress) => void;
  onSynced?: (item: QueuedDriverUpload) => void;
}): Promise<{ synced: number; remaining: number }> {
  if (typeof window === "undefined" || !window.navigator.onLine) {
    return { synced: 0, remaining: readQueue().length };
  }

  let queue = readQueue();
  let synced = 0;

  for (const item of queue) {
    if (item.attempts >= MAX_RETRY_ATTEMPTS) continue;

    try {
      const file = dataUrlToFile(item.dataUrl, item.fileName, item.fileType);
      await uploadDriverDocumentWithProgress({
        organizationId: options.organizationId,
        documentType: item.documentType,
        file,
        loadId: item.loadId,
        onProgress: (progress) => options.onProgress?.(item, progress),
      });
      synced += 1;
      options.onSynced?.(item);
      queue = readQueue().filter((queued) => queued.id !== item.id);
      writeQueue(queue);
    } catch (error: unknown) {
      queue = readQueue().map((queued) =>
        queued.id === item.id
          ? {
              ...queued,
              attempts: queued.attempts + 1,
              lastError: error instanceof Error ? error.message : "Retry failed.",
            }
          : queued
      );
      writeQueue(queue);
      break;
    }
  }

  return { synced, remaining: readQueue().length };
}
