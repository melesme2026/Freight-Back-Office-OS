"use client";

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ApiClientError } from "@/lib/api-client";
import {
  clearPortalToken,
  downloadPortalDocument,
  downloadPortalPacket,
  fetchPortalLoad,
  fetchPortalScope,
  getPortalToken,
  PortalDocument,
  PortalLoad,
  PortalPacket,
  PortalScope,
  setPortalToken,
  uploadPortalDocument,
  validatePortalUploadFile,
} from "@/lib/portal";

type PortalRuntimeProps = { routeLoadId?: string };

const UPLOAD_TYPES = [
  { value: "rate_confirmation", label: "Revised rate confirmation" },
  { value: "bill_of_lading", label: "Bill of lading" },
  { value: "proof_of_delivery", label: "Proof of delivery" },
  { value: "lumper_receipt", label: "Lumper receipt" },
  { value: "accessorial_support", label: "Accessorial support" },
  { value: "detention_support", label: "Detention support" },
  { value: "scale_ticket", label: "Scale ticket" },
  { value: "other", label: "Other paperwork" },
];

function formatDate(value: string | null | undefined): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatStatus(value: string | null | undefined): string {
  if (!value) return "Pending";
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function friendlyError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) return "This portal link is expired or invalid. Ask your carrier contact for a new secure link.";
    if (error.status === 403) return error.message || "This action is not allowed for your portal link.";
  }
  return error instanceof Error ? error.message : "Portal action failed. Please try again.";
}

export function PortalRuntime({ routeLoadId }: PortalRuntimeProps) {
  const [tokenInput, setTokenInput] = useState("");
  const [scope, setScope] = useState<PortalScope | null>(null);
  const [load, setLoad] = useState<PortalLoad | null>(null);
  const [documents, setDocuments] = useState<PortalDocument[]>([]);
  const [packets, setPackets] = useState<PortalPacket[]>([]);
  const [documentType, setDocumentType] = useState(UPLOAD_TYPES[0].value);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadPortal = useCallback(async (token?: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    const scoped = await fetchPortalScope(token);
    if (routeLoadId && routeLoadId !== scoped.scope.load_id) {
      throw new Error("This secure portal link is scoped to a different load.");
    }
    const detail = await fetchPortalLoad(scoped.scope.load_id, token);
    setScope(scoped.scope);
    setLoad(detail.load);
    setDocuments(detail.documents);
    setPackets(detail.packets);
    setIsLoading(false);
  }, [routeLoadId]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token")?.trim();
    if (token) {
      setPortalToken(token);
      window.history.replaceState({}, "", window.location.pathname);
    }
    const savedToken = token || getPortalToken();
    if (!savedToken) {
      setIsLoading(false);
      return;
    }
    void loadPortal(savedToken).catch((error: unknown) => {
      setIsLoading(false);
      clearPortalToken();
      setErrorMessage(friendlyError(error));
    });
  }, [loadPortal]);

  const latestPacket = packets[0];
  const requiredDocs = useMemo(() => load?.packet_readiness?.required_documents ?? ["invoice", "rate_confirmation", "proof_of_delivery"], [load]);
  const missingDocs = useMemo(() => load?.packet_readiness?.missing_documents ?? [], [load]);

  async function unlockPortal() {
    if (!tokenInput.trim()) return;
    setPortalToken(tokenInput);
    await loadPortal(tokenInput).catch((error: unknown) => {
      clearPortalToken();
      setErrorMessage(friendlyError(error));
    });
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !scope) return;
    const validation = validatePortalUploadFile(file);
    if (validation) {
      setErrorMessage(validation);
      return;
    }
    setIsUploading(true);
    setMessage(null);
    setErrorMessage(null);
    try {
      const uploaded = await uploadPortalDocument(scope.load_id, documentType, file);
      setDocuments((current) => [uploaded, ...current]);
      setMessage("Document uploaded securely. Your carrier team can now review it.");
      await loadPortal();
    } catch (error) {
      setErrorMessage(friendlyError(error));
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  async function handlePacketDownload(packet: PortalPacket) {
    if (!scope) return;
    try {
      const blob = await downloadPortalPacket(scope.load_id, packet.id);
      saveBlob(blob, `packet-${load?.load_number ?? scope.load_id}.zip`);
    } catch (error) {
      setErrorMessage(friendlyError(error));
    }
  }

  async function handleDocumentDownload(document: PortalDocument) {
    if (!scope) return;
    try {
      const blob = await downloadPortalDocument(scope.load_id, document.id);
      saveBlob(blob, document.original_filename || `${document.document_type || "document"}.pdf`);
    } catch (error) {
      setErrorMessage(friendlyError(error));
    }
  }

  if (isLoading) {
    return <main className="min-h-screen bg-slate-950 px-4 py-8 text-white"><div className="mx-auto max-w-5xl rounded-3xl border border-white/10 bg-white/10 p-8">Loading secure portal…</div></main>;
  }

  if (!scope || !load) {
    return (
      <main className="min-h-screen bg-slate-950 px-4 py-8 text-white">
        <section className="mx-auto max-w-xl rounded-3xl border border-white/10 bg-white p-6 text-slate-950 shadow-2xl sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-700">ADWA Freight secure portal</p>
          <h1 className="mt-3 text-3xl font-bold">Open your load portal</h1>
          <p className="mt-3 text-slate-600">Paste the secure access token from your invitation. Links are scoped to one load and expire automatically.</p>
          {errorMessage ? <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div> : null}
          <label className="mt-6 block text-sm font-semibold text-slate-700" htmlFor="portal-token">Secure access token</label>
          <textarea id="portal-token" className="mt-2 min-h-28 w-full rounded-2xl border border-slate-300 p-3 text-sm" value={tokenInput} onChange={(event) => setTokenInput(event.target.value)} />
          <button type="button" onClick={unlockPortal} className="mt-4 w-full rounded-2xl bg-emerald-700 px-4 py-3 font-semibold text-white shadow-lg shadow-emerald-950/20">Unlock portal</button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <section className="bg-slate-950 px-4 py-8 text-white sm:py-10">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-300">Secure external operations portal</p>
            <h1 className="mt-3 text-3xl font-bold sm:text-5xl">Load {load.load_number || load.id.slice(0, 8)}</h1>
            <p className="mt-3 max-w-2xl text-slate-300">Scoped access for {scope.contact_email}. This view only includes the authorized shipment, billing packet status, and controlled document upload actions.</p>
          </div>
          <button type="button" onClick={() => { clearPortalToken(); window.location.assign("/portal"); }} className="rounded-2xl border border-white/20 px-4 py-3 text-sm font-semibold text-white">Sign out</button>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 py-6 md:grid-cols-4">
        {[{ label: "Load status", value: formatStatus(load.status) }, { label: "Pickup", value: formatDate(load.pickup_date) }, { label: "Delivery", value: formatDate(load.delivery_date) }, { label: "Packet", value: load.documents_complete ? "Complete" : "In progress" }].map((item) => (
          <div key={item.label} className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-medium text-slate-500">{item.label}</p>
            <p className="mt-2 text-xl font-bold">{item.value}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 pb-10 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
            <h2 className="text-2xl font-bold">Shipment visibility</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Pickup</p><p className="mt-1 font-semibold">{load.pickup_location || "Not available"}</p></div>
              <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Delivery</p><p className="mt-1 font-semibold">{load.delivery_location || "Not available"}</p></div>
              <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Customer</p><p className="mt-1 font-semibold">{load.customer_account_name || "Not available"}</p></div>
              <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Broker</p><p className="mt-1 font-semibold">{load.broker_name || "Not available"}</p></div>
            </div>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div><h2 className="text-2xl font-bold">Packet visibility</h2><p className="text-sm text-slate-500">Invoice packet status and safe document availability.</p></div>
              {latestPacket && scope.allow_packet_download ? <button type="button" onClick={() => handlePacketDownload(latestPacket)} className="rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white">Download packet</button> : null}
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {requiredDocs.map((doc) => <div key={doc} className={`rounded-2xl p-4 ${missingDocs.includes(doc) ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900"}`}><p className="text-sm font-semibold">{formatStatus(doc)}</p><p className="mt-1 text-xs">{missingDocs.includes(doc) ? "Needed" : "Received"}</p></div>)}
            </div>
            <div className="mt-5 space-y-3">
              {packets.length === 0 ? <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">No packet has been published for this load yet.</p> : packets.map((packet) => <div key={packet.id} className="flex flex-col gap-2 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold">{packet.packet_reference || "Packet"}</p><p className="text-sm text-slate-500">{formatStatus(packet.status)} · Sent {formatDate(packet.sent_at)}</p></div>{scope.allow_packet_download ? <button type="button" onClick={() => handlePacketDownload(packet)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold">Download</button> : null}</div>)}
            </div>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
            <h2 className="text-2xl font-bold">Documents</h2>
            <div className="mt-4 divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200">
              {documents.length === 0 ? <p className="p-4 text-sm text-slate-600">No documents are visible yet.</p> : documents.map((document) => <div key={document.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold">{formatStatus(document.document_type)}</p><p className="text-sm text-slate-500">{document.original_filename || "Uploaded document"} · {formatDate(document.received_at)}</p></div>{document.download_allowed ? <button type="button" onClick={() => handleDocumentDownload(document)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold">Download</button> : null}</div>)}
            </div>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
            <h2 className="text-2xl font-bold">Upload paperwork</h2>
            <p className="mt-2 text-sm text-slate-600">Upload revised rate confirmations, signed documents, lumper receipts, or supporting paperwork. Files are attributed to your portal identity.</p>
            {message ? <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</div> : null}
            {errorMessage ? <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div> : null}
            {scope.allow_document_upload ? <div className="mt-5 space-y-3"><label className="block text-sm font-semibold" htmlFor="document-type">Document type</label><select id="document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="w-full rounded-2xl border border-slate-300 p-3">{UPLOAD_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select><label className="flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm font-semibold text-slate-700"><span>{isUploading ? "Uploading…" : "Tap to choose PDF or image"}</span><input type="file" className="sr-only" accept="application/pdf,image/*" disabled={isUploading} onChange={handleUpload} /></label></div> : <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">Uploads are disabled for this secure link.</p>}
          </div>
          <div className="rounded-3xl bg-slate-950 p-5 text-white shadow-sm sm:p-6">
            <h2 className="text-xl font-bold">Security scope</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-300"><li>• One organization</li><li>• One load only</li><li>• No analytics, billing admin, or dispatch command center access</li><li>• All portal actions are audit logged</li></ul>
          </div>
        </aside>
      </section>
    </main>
  );
}
