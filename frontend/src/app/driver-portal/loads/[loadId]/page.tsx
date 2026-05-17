"use client";

/* eslint-disable @next/next/no-img-element */

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ApiClientError, apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import {
  DRIVER_WORKFLOW_STEPS,
  checklistFromReadiness,
  documentCompletion,
  documentStatusFromProcessingStatus,
  getMissingRequiredDocuments,
  labelForDocumentType,
  nextActionForLoad,
  statusClasses,
  statusLabel,
  toDriverStatus,
  workflowStepState,
} from "@/lib/driver-portal";
import {
  enqueueDriverUpload,
  uploadDriverDocumentWithProgress,
  validateDriverUploadFile,
} from "@/lib/driver-mobile";
import { canonicalDocumentType } from "@/lib/document-types";

type DriverDocument = {
  id: string;
  document_type: string | null;
  original_filename: string | null;
  processing_status: string | null;
  received_at: string | null;
};

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
    if (error.status === 409) return "A required document already exists. Choose replace if dispatch requested a new copy.";
    if (error.status === 401 || error.status === 403) return "You do not have access to upload for this load. Contact dispatch if this looks wrong.";
    if (error.status >= 500) return "The upload service is temporarily unavailable. Your file was not accepted yet; please retry in a moment.";
  }
  if (typeof window !== "undefined" && !window.navigator.onLine) return "You appear offline. We’ll queue the upload and retry when connection returns.";
  return error instanceof Error ? error.message : "Upload did not finish. Please try again.";
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
      setErrorMessage(error instanceof Error ? error.message : "Load details could not refresh. Try again or contact dispatch.");
    });
  }, [fetchLoad]);

  const documentStatuses = useMemo(() => {
    return documents.reduce<Record<string, ReturnType<typeof documentStatusFromProcessingStatus>>>((acc, document) => {
      const documentType = canonicalDocumentType(document.document_type);
      if (documentType !== "unknown") acc[documentType] = documentStatusFromProcessingStatus(document.processing_status);
      return acc;
    }, {});
  }, [documents]);

  const checklist = useMemo(() => checklistFromReadiness(asRecord(loadData?.packet_readiness), documentStatuses), [loadData, documentStatuses]);
  const missingRequiredDocs = getMissingRequiredDocuments(checklist);
  const completion = documentCompletion(checklist);
  const nextAction = nextActionForLoad({ rawStatus: asText(loadData?.status, "booked"), checklist });
  const timelineStates = workflowStepState(asText(loadData?.status, "booked"), checklist);

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
      event.target.value = "";
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
        setSuccessMessage(`Dispatch received your ${labelForDocumentType(documentType)}. Accounting can review it once the packet is complete.`);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Upload error.";
        if (message.includes("duplicate_required_document") || message.toLowerCase().includes("already exists")) {
          setPendingReplace({ documentType, file, message: `${labelForDocumentType(documentType)} is already on file. Replace it only if dispatch requested a newer copy.` });
          return;
        }
        throw error;
      }
      await fetchLoad();
    } catch (error: unknown) {
      if (typeof window !== "undefined" && (!window.navigator.onLine || error instanceof TypeError || (error instanceof Error && error.message.toLowerCase().includes("network")))) {
        try {
          await enqueueDriverUpload({ file, documentType, loadId });
          setSuccessMessage(`Offline: ${labelForDocumentType(documentType)} is queued and will retry when connection returns.`);
        } catch (queueError: unknown) {
          setErrorMessage(queueError instanceof Error ? queueError.message : "Upload failed and could not be queued. Please retry when connected.");
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
      setSuccessMessage(`${labelForDocumentType(pendingReplace.documentType)} replaced. Dispatch will review the newest copy.`);
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
      setSuccessMessage(nextStatus === "delivered" ? "Delivery marked complete. Upload the signed POD if it is not already on file." : "In-transit / ETA update sent to dispatch.");
      await fetchLoad();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Dispatch did not receive the update. Please retry when connected.");
    } finally {
      setIsUpdatingEta(false);
    }
  }

  const status = toDriverStatus(asText(loadData?.status, "booked"), missingRequiredDocs.length > 0);
  const operationalNotes = asOptionalText(loadData?.notes);

  return (
    <main className="safe-page min-h-screen overflow-x-hidden bg-slate-50 pb-24 text-slate-900 sm:pb-10">
      <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6 sm:py-10">
        <Link href="/driver-portal" className="text-sm font-bold text-brand-700">← Driver workspace</Link>

        <section className="mt-4 overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 shadow-soft">
          <div className="bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.28),transparent_35%),linear-gradient(135deg,#020617,#0f172a)] p-5 text-white sm:p-6">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-white/55">Active load detail</p>
            <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="min-w-0">
                <h1 className="break-words text-3xl font-black tracking-tight sm:text-4xl">{loadData ? `Load ${asText(loadData.load_number)}` : "Loading load..."}</h1>
                <p className="mt-3 text-lg font-semibold text-white/90">{asText(loadData?.pickup_location)} → {asText(loadData?.delivery_location)}</p>
                <p className="mt-2 text-sm text-white/60">{asOptionalText(loadData?.broker_name) ?? asOptionalText(loadData?.customer_account_name) ?? "Broker/customer details not provided"}</p>
              </div>
              <div className="rounded-3xl border border-white/15 bg-white/10 p-4 backdrop-blur lg:w-80">
                <div className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-black capitalize text-slate-950">{status}</span>
                  <span className="text-xs font-semibold text-white/70">{completion.completed}/{completion.total} required</span>
                </div>
                <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-emerald-400" style={{ width: `${completion.percent}%` }} /></div>
                <p className="mt-3 text-sm leading-6 text-white/72">{nextAction.title}</p>
              </div>
            </div>
          </div>
        </section>

        <section className={`mt-5 rounded-[2rem] border p-5 shadow-soft ${nextAction.tone === "blocked" ? "border-rose-200 bg-rose-50" : nextAction.tone === "success" ? "border-emerald-200 bg-emerald-50" : nextAction.tone === "waiting" ? "border-sky-200 bg-sky-50" : "border-amber-200 bg-amber-50"}`}>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-600">Next Action Center</p>
          <h2 className="mt-2 text-2xl font-black text-slate-950">{nextAction.title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-700">{nextAction.description}</p>
        </section>

        <section className="mt-5 grid gap-4 lg:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-soft">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Pickup</p>
            <p className="mt-2 text-lg font-black text-slate-950">{asText(loadData?.pickup_location)}</p>
            <p className="mt-1 text-sm text-slate-500">Appointment/reference: {asText(loadData?.rate_confirmation_number, "Not provided")}</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-soft">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Delivery</p>
            <p className="mt-2 text-lg font-black text-slate-950">{asText(loadData?.delivery_location)}</p>
            <p className="mt-1 text-sm text-slate-500">BOL/reference: {asText(loadData?.bol_number, "Not provided")}</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-soft">
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">Operations note</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{operationalNotes ?? "No special instructions from dispatch are attached to this load."}</p>
          </div>
        </section>

        <section className="mt-5 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-brand-700">Load Timeline</p>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            {DRIVER_WORKFLOW_STEPS.map((step) => {
              const state = timelineStates[step.key];
              return <div key={step.key} className={`rounded-2xl border px-3 py-3 text-xs font-bold ${state === "done" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : state === "current" ? "border-brand-200 bg-brand-50 text-brand-800" : "border-slate-200 bg-slate-50 text-slate-500"}`}><div className="mb-2 h-2 rounded-full bg-current opacity-50" />{step.label}</div>;
            })}
          </div>
        </section>

        <section role="region" aria-labelledby="driver-eta-check-in-heading" className="mt-5 rounded-[2rem] border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-soft">
          <h2 id="driver-eta-check-in-heading" className="text-xl font-black text-slate-900">ETA / check-in</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">Send one-time status, ETA, and optional location check-ins to dispatch. This does not enable continuous tracking.</p>
          <label htmlFor="driver-eta" className="mt-4 block text-xs font-bold uppercase tracking-wide text-slate-600">ETA note</label>
          <input id="driver-eta" value={etaValue} onChange={(event) => setEtaValue(event.target.value)} placeholder="Example: Arriving 3:30 PM, delayed by shipper" className="touch-target mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 text-base sm:text-sm" />
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button type="button" onClick={() => void handleDriverStatusUpdate("in_transit")} disabled={isUpdatingEta} className="touch-target rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white disabled:bg-slate-300">{isUpdatingEta ? "Sending..." : "Send in-transit / ETA"}</button>
            <button type="button" onClick={() => void handleDriverStatusUpdate("delivered")} disabled={isUpdatingEta} className="touch-target rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800 disabled:opacity-60">Mark delivered</button>
          </div>
        </section>

        {errorMessage ? <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {successMessage ? <div role="status" aria-live="polite" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{successMessage}</div> : null}
        {pendingReplace ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"><p className="font-semibold">{pendingReplace.message}</p><p className="mt-1 text-xs">Replacing keeps the workflow scoped to this load and makes the newest file the copy dispatch reviews.</p><div className="mt-3 flex flex-col gap-2 sm:flex-row"><button type="button" className="touch-target rounded-lg bg-amber-600 px-4 py-3 text-sm font-semibold text-white" onClick={() => void handleReplaceUpload()} disabled={Boolean(uploadingType)}>Replace existing</button><button type="button" className="touch-target rounded-lg border border-amber-300 bg-white px-4 py-3 text-sm font-semibold text-amber-900" onClick={() => setPendingReplace(null)} disabled={Boolean(uploadingType)}>Keep current file</button></div></div> : null}
        {selectedPreview ? <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700"><p className="font-semibold">Camera preview: {labelForDocumentType(selectedPreview.documentType)}</p><p className="mt-1 break-all text-xs text-slate-500">{selectedPreview.name}</p><img src={selectedPreview.url} alt="Selected upload preview" className="mt-3 max-h-72 w-full rounded-xl border border-slate-200 object-contain" /></div> : null}
        {uploadProgress !== null ? <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3" aria-label="Upload progress"><div className="h-3 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${uploadProgress}%` }} /></div><p className="mt-1 text-xs font-semibold text-slate-600">Uploading safely: {uploadProgress}%</p></div> : null}

        <section role="region" className="mt-6 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft" aria-labelledby="driver-document-uploads-heading">
          <h2 id="driver-document-uploads-heading" className="text-xl font-black text-slate-900">Document checklist</h2>
          <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <p className="font-bold">What dispatch/accounting is waiting on</p>
            <p className="mt-1 text-sm">{missingRequiredDocs.length === 0 ? "All required paperwork is submitted. Accounting is reviewing your packet." : `Still needed: ${missingRequiredDocs.map((item) => item.label).join(", ")}.`}</p>
            <p className="mt-1 text-xs">Accepted files: PDF/JPG/PNG/WEBP/HEIC/HEIF/TIFF · Max file size: 15MB</p>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {checklist.map((item) => (
              <div key={item.type} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="font-black text-slate-900">{item.label}</div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">{item.required ? "Required" : "Optional"}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.helper}</p>
                  </div>
                  <span className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-black ${statusClasses(item.status)}`}>{statusLabel(item.status)}</span>
                </div>
                {item.status !== "approved" ? <label className="touch-target mt-3 inline-flex w-full cursor-pointer items-center justify-center rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white sm:w-auto">{uploadingType === item.type ? "Uploading..." : item.status === "missing" ? `Upload ${item.label}` : `Add / replace ${item.label}`}<input type="file" aria-label={`Upload ${item.label} file or photo`} accept="image/*,application/pdf" capture="environment" className="sr-only" onChange={(event) => void uploadDocument(item.type, event)} disabled={Boolean(uploadingType)} /></label> : null}
              </div>
            ))}
          </div>
        </section>

        <section className="mt-6 rounded-[2rem] border border-slate-200 bg-white p-5 shadow-soft">
          <h2 className="text-xl font-black text-slate-900">Upload history</h2>
          <p className="mt-1 text-sm text-slate-600">Files appear here as soon as dispatch receives them. Statuses show whether the back office is reviewing, approved, or requesting a cleaner copy.</p>
          <div className="mt-3 space-y-2">
            {documents.length === 0 ? <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">No documents submitted for this load yet.</div> : documents.map((document) => {
              const docStatus = documentStatusFromProcessingStatus(document.processing_status);
              return <div key={document.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-3 text-sm sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="font-bold text-slate-900">{labelForDocumentType(document.document_type ?? "other")}</div><div className="break-all text-xs text-slate-600">{document.original_filename ?? "Uploaded document"}</div></div><div className="text-xs text-slate-500 sm:text-right"><span className={`inline-flex rounded-full border px-3 py-1 font-black ${statusClasses(docStatus)}`}>{statusLabel(docStatus)}</span><div className="mt-1">{formatDateTime(document.received_at)}</div></div></div>;
            })}
          </div>
        </section>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 p-3 shadow-2xl backdrop-blur sm:hidden">
        <a href="#driver-document-uploads-heading" className="touch-target flex items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white">{missingRequiredDocs.length > 0 ? `Upload ${missingRequiredDocs[0].label}` : "Review document status"}</a>
      </div>
    </main>
  );
}
