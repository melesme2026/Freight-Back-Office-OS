import { ApiClientError, apiClient } from "@/lib/api-client";

export type DownloadOptions = {
  filename: string;
  timeoutMs?: number;
  token?: string;
  organizationId?: string;
};

export function friendlyDownloadError(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError && error.code === "client_timeout") {
    return "Download is taking longer than expected. Check your connection, then try again or refresh the page.";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1_000);
}

export async function downloadBlobFromApi(path: string, options: DownloadOptions): Promise<void> {
  const blob = await apiClient.getBlob(path, {
    token: options.token,
    organizationId: options.organizationId,
    timeoutMs: options.timeoutMs ?? 10_000,
    dedupe: false,
    retry: false,
  });
  saveBlob(blob, options.filename);
}
