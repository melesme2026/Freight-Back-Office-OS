"use client";

/* eslint-disable @next/next/no-img-element */

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { labelForDocumentType, toDriverStatus } from "@/lib/driver-portal";
import {
  enqueueDriverUpload,
  uploadDriverDocumentWithProgress,
  validateDriverUploadFile,
} from "@/lib/driver-mobile";

type ChecklistItem = { type: string; required: boolean; uploaded: boolean };
type DriverDocument = {
  id: string;
  document_type: string | null;
  original_filename: string | null;
  processing_status: string | null;
  received_at: string | null;
};

const CHECKLIST: ChecklistItem[] = [
  { type: "rate_confirmation", required: false, uploaded: false },
  { type: "bill_of_lading", required: true, uploaded: false },
  { type: "proof_of_delivery", required: true, uploaded: false },
  { type: "lumper_receipt", required: false, uploaded: false },
  { type: "scale_ticket", required: false, uploaded: false },
  { type: "other", required: false, uploaded: false },
];

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asText(value: unknown, fallback = "—"): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asOptionalText(value: unknown): string | null {
  const text = asText(value, "");
  return text || null;
}

function unwrapApiData(payload: unknown): Record<string, unknown> | null {
  const root = asRecord(payload);
  const data = asRecord(root?.data);
  return data ?? root;
}

function normalizeDocuments(payload: unknown): DriverDocument[] {
  const root = asRecord(payload);
  const items = Array.isArray(root?.data) ? root.data : Array.isArray(payload) ? payload : [];

  return items
    .map((item) => {
      const record = asRecord(item);
      const id = asOptionalText(record?.id);
      if (!record || !id) return null;
      return {
        id,
        document_type: asOptionalText(record.document_type),
        original_filename: asOptionalText(record.original_filename) ?? asOptionalText(record.file_name),
        processing_status: asOptionalText(record.processing_status),
        received_at: asOptionalText(record.received_at) ?? asOptionalText(record.created_at),
      };
    })
    .filter((item): item is DriverDocument => item !== null);
}

function formatDateTime(value: string | null): string {
  if (!value) return "Submitted just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function friendlyUploadError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 409) return error.message || "A document already exists for this load.";
    if (error.status === 401 || error.status === 403) return "You do not have access to upload for this load. Contact dispatch if this looks wrong.";
  }
  return error instanceof Error ? error.message : "Upload error. Please try again.";
}

export default function DriverLoadDetailPage() {
  const params = useParams<{ loadId: string }>();
  const loadId = params?.loadId;
  const [loadData, setLoadData] = useState<Record<string, unknown> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [pendingReplace, setPendingReplace] = useState<{ documentType: string; file: File; message: string } | null>(null);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [selectedPreview, setSelectedPreview] = useState<{ documentType: string; url: string; name: string } | null>(null);
  const [etaValue, setEtaValue] = useState("");
  const [isUpdatingEta, setIsUpdatingEta] = useState(false);
  const [documents, setDocuments] = useState<DriverDocument[]>([]);

  const fetchLoad = useCallback(async () => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    if (!organizationId || !loadId) return;

    const [loadPayload, documentPayload] = await Promise.all([
      apiClient.get<unknown>(`/driver/loads/${loadId}`, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      }),
      apiClient.get<unknown>(`/loads/${loadId}/documents?page=1&page_size=25`, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      }),
    ]);

    setLoadData(unwrapApiData(loadPayload));
    setDocuments(normalizeDocuments(documentPayload));
  }, [loadId]);

  useEffect(() => {
    setErrorMessage(null);
    void fetchLoad().catch((error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load load detail.");
    });
  }, [fetchLoad]);

  const checklist = useMemo(() => {
    const readiness = asRecord(loadData?.packet_readiness);
    const present = Array.isArray(readiness?.present_documents)
      ? readiness.present_documents.filter((item) => typeof item === "string")
      : [];

    return CHECKLIST.map((item) => ({ ...item, uploaded: present.includes(item.type) }));
  }, [loadData]);
  const missingRequiredDocs = checklist.filter((item) => item.required && !item.uploaded);

  useEffect(() => {
    return () => {
      if (selectedPreview?.url) URL.revokeObjectURL(selectedPreview.url);
    };
  }, [selectedPreview]);

  async function uploadDocument(documentType: string, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !loadId) return;

    const organizationId = getOrganizationId();
    if (!organizationId) return;

    const validationError = validateDriverUploadFile(file);
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    if (file.type.startsWith("image/")) {
      if (selectedPreview?.url) URL.revokeObjectURL(selectedPreview.url);
      setSelectedPreview({ documentType, url: URL.createObjectURL(file), name: file.name });
    } else {
      setSelectedPreview(null);
    }

    try {
      setUploadingType(documentType);
      setErrorMessage(null);
      setSuccessMessage(null);
      try {
        setUploadProgress(0);
        await uploadDriverDocumentWithProgress({
          organizationId,
          documentType,
          file,
          loadId,
          onProgress: (progress) => setUploadProgress(progress.percent),
        });
        setSuccessMessage(`Upload successful: ${file.name} (${labelForDocumentType(documentType)}).`);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Upload error.";
        if (message.includes("duplicate_required_document") || message.toLowerCase().includes("already exists")) {
          setPendingReplace({ documentType, file, message: "A required document already exists for this load." });
          return;
        } else {
          throw error;
        }
      }
      await fetchLoad();
    } catch (error: unknown) {
      if (typeof window !== "undefined" && (!window.navigator.onLine || error instanceof TypeError || (error instanceof Error && error.message.toLowerCase().includes("network")))) {
        try {
          await enqueueDriverUpload({ file, documentType, loadId });
          setSuccessMessage(`Offline: queued ${file.name}. It will retry when your connection returns.`);
        } catch (queueError: unknown) {
          setErrorMessage(queueError instanceof Error ? queueError.message : "Upload failed and could not be queued.");
        }
      } else {
        setErrorMessage(friendlyUploadError(error));
      }
    } finally {
      setUploadingType(null);
      setUploadProgress(null);
      event.target.value = "";
    }
  }


  async function handleReplaceUpload() {
    if (!pendingReplace || !loadId) return;
    const organizationId = getOrganizationId();
    if (!organizationId) return;
    try {
      setUploadingType(pendingReplace.documentType);
      setUploadProgress(0);
      await uploadDriverDocumentWithProgress({
        organizationId,
        documentType: pendingReplace.documentType,
        file: pendingReplace.file,
        loadId,
        replace: true,
        onProgress: (progress) => setUploadProgress(progress.percent),
      });
      setPendingReplace(null);
      setSuccessMessage("Document replaced.");
      await fetchLoad();
    } catch (error: unknown) {
      setErrorMessage(friendlyUploadError(error));
    } finally {
      setUploadingType(null);
      setUploadProgress(null);
    }
  }

  async function handleDriverStatusUpdate(nextStatus: "in_transit" | "delivered") {
    if (!loadId || isUpdatingEta) return;
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    if (!organizationId) return;

    setIsUpdatingEta(true);
    setErrorMessage(null);
    try {
      let location: { latitude: number; longitude: number; accuracy: number | null } | null = null;
      if (typeof window !== "undefined" && "geolocation" in navigator) {
        try {
          const permission = "permissions" in navigator
            ? await navigator.permissions.query({ name: "geolocation" as PermissionName })
            : null;
          if (permission?.state === "granted") {
            const position = await new Promise<GeolocationPosition>((resolve, reject) => {
              navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: false,
                timeout: 3000,
                maximumAge: 300000,
              });
            });
            location = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
            };
          }
        } catch {
          location = null;
        }
      }
      await apiClient.post(`/driver/loads/${loadId}/check-in`, {
        status: nextStatus,
        eta_note: etaValue.trim() || null,
        latitude: location?.latitude ?? null,
        longitude: location?.longitude ?? null,
        location_accuracy_meters: location?.accuracy ?? null,
      }, { token: token ?? undefined, organizationId: organizationId ?? undefined });
      setSuccessMessage(nextStatus === "delivered" ? "Delivery status sent to dispatch." : "In-transit / ETA update sent to dispatch.");
      await fetchLoad();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update load status.");
    } finally {
      setIsUpdatingEta(false);
    }
  }

  const status = toDriverStatus(asText(loadData?.status, "booked"), checklist.some((item) => item.required && !item.uploaded));

  return (
    <main className="safe-page min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <h1 className="text-2xl font-bold text-slate-950">{loadData ? `Load ${asText(loadData.load_number)}` : "Loading load..."}</h1>
        <div className="mt-3 space-y-1 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <div>Pickup: {asText(loadData?.pickup_location)}</div>
          <div>Delivery: {asText(loadData?.delivery_location)}</div>
          <div>Driver: {asText(loadData?.driver_name)}</div>
          <div className="font-semibold capitalize">Status: {status}</div>
        </div>

        <section role="region" aria-labelledby="driver-eta-check-in-heading" className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <h2 id="driver-eta-check-in-heading" className="text-lg font-semibold text-slate-900">ETA / check-in</h2>
          <p className="mt-1 text-xs text-slate-500">Send one-time status, ETA, and optional location check-ins to dispatch. This does not enable continuous tracking.</p>
          <label htmlFor="driver-eta" className="mt-4 block text-xs font-semibold uppercase tracking-wide text-slate-600">ETA note</label>
          <input
            id="driver-eta"
            value={etaValue}
            onChange={(event) => setEtaValue(event.target.value)}
            placeholder="Example: Arriving 3:30 PM, delayed by shipper"
            className="touch-target mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 text-base sm:text-sm"
          />
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button type="button" onClick={() => void handleDriverStatusUpdate("in_transit")} disabled={isUpdatingEta} className="touch-target rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-300">
              {isUpdatingEta ? "Sending..." : "Send in-transit / ETA"}
            </button>
            <button type="button" onClick={() => void handleDriverStatusUpdate("delivered")} disabled={isUpdatingEta} className="touch-target rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800 disabled:opacity-60">
              Mark delivered
            </button>
          </div>
        </section>

        {errorMessage ? <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {successMessage ? <div role="status" aria-live="polite" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{successMessage}</div> : null}
        {pendingReplace ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"><p className="font-semibold">{pendingReplace.message}</p><div className="mt-2 flex flex-col gap-2 sm:flex-row"><button type="button" className="touch-target rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white" onClick={() => void handleReplaceUpload()} disabled={Boolean(uploadingType)}>Replace existing</button><button type="button" className="touch-target rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-900" onClick={() => setPendingReplace(null)} disabled={Boolean(uploadingType)}>Cancel</button></div></div> : null}
        {selectedPreview ? (
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
            <p className="font-semibold">Camera preview: {labelForDocumentType(selectedPreview.documentType)}</p>
            <p className="mt-1 break-all text-xs text-slate-500">{selectedPreview.name}</p>
            <img src={selectedPreview.url} alt="Selected upload preview" className="mt-3 max-h-72 w-full rounded-xl border border-slate-200 object-contain" />
          </div>
        ) : null}
        {uploadProgress !== null ? (
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3" aria-label="Upload progress">
            <div className="h-3 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="mt-1 text-xs font-semibold text-slate-600">Uploading: {uploadProgress}%</p>
          </div>
        ) : null}

        <section role="region" className="mt-6 rounded-2xl border border-slate-200 bg-white p-4" aria-labelledby="driver-document-uploads-heading">
          <h2 id="driver-document-uploads-heading" className="text-lg font-semibold text-slate-900">Document Uploads</h2>
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <p className="font-semibold">What is missing</p>
            <p className="mt-1 text-xs">
              {missingRequiredDocs.length === 0
                ? "All required driver documents are uploaded."
                : `Still needed: ${missingRequiredDocs.map((item) => labelForDocumentType(item.type)).join(", ")}.`}
            </p>
            <p className="mt-1 text-xs">Accepted files: PDF/JPG/PNG/WEBP/HEIC/HEIF/TIFF · Max file size: 15MB</p>
          </div>
          <div className="mt-3 space-y-3">
            {checklist.map((item) => (
              <div key={item.type} className="rounded-xl border border-slate-200 p-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="font-medium text-slate-900">{labelForDocumentType(item.type)}</div>
                    <div className="text-xs text-slate-600">{item.required ? "Required" : "Optional"}</div>
                  </div>
                  <div className={`text-xs font-semibold ${item.uploaded ? "text-emerald-700" : "text-amber-700"}`}>{item.uploaded ? "Uploaded" : "Missing"}</div>
                </div>

                {!item.uploaded ? (
                  <label className="touch-target mt-3 inline-flex w-full cursor-pointer items-center justify-center rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white sm:w-auto">
                    {uploadingType === item.type ? "Uploading..." : `Upload ${labelForDocumentType(item.type)}`}
                    <input type="file" aria-label={`Upload ${labelForDocumentType(item.type)} file or photo`} accept="image/*,application/pdf" capture="environment" className="sr-only" onChange={(event) => void uploadDocument(item.type, event)} disabled={Boolean(uploadingType)} />
                  </label>
                ) : null}
              </div>
            ))}
          </div>
        </section>
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="text-lg font-semibold text-slate-900">Submitted documents</h2>
          <p className="mt-1 text-sm text-slate-600">Your uploaded documents for this assigned load appear here immediately after a successful upload.</p>
          <div className="mt-3 space-y-2">
            {documents.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">No documents submitted for this load yet.</div>
            ) : (
              documents.map((document) => (
                <div key={document.id} className="flex flex-col gap-2 rounded-xl border border-slate-200 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900">{labelForDocumentType(document.document_type ?? "other")}</div>
                    <div className="break-all text-xs text-slate-600">{document.original_filename ?? "Uploaded document"}</div>
                  </div>
                  <div className="text-xs text-slate-500 sm:text-right">
                    <div className="font-semibold capitalize text-emerald-700">{document.processing_status ?? "submitted"}</div>
                    <div>{formatDateTime(document.received_at)}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
