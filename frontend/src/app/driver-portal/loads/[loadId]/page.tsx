"use client";

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { labelForDocumentType, toDriverStatus } from "@/lib/driver-portal";

type ChecklistItem = { type: string; required: boolean; uploaded: boolean };

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
  return fallback;
}

export default function DriverLoadDetailPage() {
  const params = useParams<{ loadId: string }>();
  const loadId = params?.loadId;
  const [loadData, setLoadData] = useState<Record<string, unknown> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [uploadingType, setUploadingType] = useState<string | null>(null);

  const fetchLoad = useCallback(async () => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();
    if (!organizationId || !loadId) return;

    const payload = await apiClient.get<unknown>(`/driver/loads/${loadId}`, {
      token: token ?? undefined,
      organizationId: organizationId ?? undefined,
    });

    const root = asRecord(payload);
    setLoadData(asRecord(root?.data));
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

  async function uploadDocument(documentType: string, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !loadId) return;

    const token = getAccessToken();
    const organizationId = getOrganizationId();
    if (!organizationId) return;

    const allowedMime = ["application/pdf", "image/jpeg", "image/png", "image/webp", "image/jpg", "image/heic", "image/heif", "image/tiff"];
    if (!allowedMime.includes(file.type)) {
      setErrorMessage("Upload error: only PDF or image files are allowed.");
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage("Upload error: file exceeds 15MB limit.");
      return;
    }

    const formData = new FormData();
    formData.append("organization_id", organizationId);
    formData.append("document_type", documentType);
    formData.append("load_id", loadId);
    formData.append("file", file);

    try {
      setUploadingType(documentType);
      setErrorMessage(null);
      setSuccessMessage(null);
      await apiClient.post("/driver/documents/upload", formData, {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
      });
      setSuccessMessage(`${labelForDocumentType(documentType)} upload success.`);
      await fetchLoad();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Upload error.");
    } finally {
      setUploadingType(null);
      event.target.value = "";
    }
  }

  const status = toDriverStatus(asText(loadData?.status, "booked"), checklist.some((item) => item.required && !item.uploaded));

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
        <h1 className="text-2xl font-bold text-slate-950">Load {asText(loadData?.load_number)}</h1>
        <div className="mt-3 space-y-1 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <div>Pickup: {asText(loadData?.pickup_location)}</div>
          <div>Delivery: {asText(loadData?.delivery_location)}</div>
          <div>Driver: {asText(loadData?.driver_name)}</div>
          <div className="font-semibold capitalize">Status: {status}</div>
        </div>

        {errorMessage ? <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMessage}</div> : null}
        {successMessage ? <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{successMessage}</div> : null}

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="text-lg font-semibold text-slate-900">Document Uploads</h2>
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
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-medium text-slate-900">{labelForDocumentType(item.type)}</div>
                    <div className="text-xs text-slate-600">{item.required ? "Required" : "Optional"}</div>
                  </div>
                  <div className={`text-xs font-semibold ${item.uploaded ? "text-emerald-700" : "text-amber-700"}`}>{item.uploaded ? "Uploaded" : "Missing"}</div>
                </div>

                {!item.uploaded ? (
                  <label className="mt-3 inline-flex w-full cursor-pointer items-center justify-center rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white sm:w-auto">
                    {uploadingType === item.type ? "Uploading..." : `Upload ${labelForDocumentType(item.type)}`}
                    <input type="file" accept="application/pdf,image/*" className="hidden" onChange={(event) => void uploadDocument(item.type, event)} disabled={Boolean(uploadingType)} />
                  </label>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
