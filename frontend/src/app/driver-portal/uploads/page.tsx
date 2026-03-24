"use client";

import { useState } from "react";

const recentUploads = [
  {
    id: "doc-1001",
    filename: "rate_confirmation_1001.pdf",
    type: "rate_confirmation",
    status: "processed",
    uploadedAt: "2026-03-23 09:10 AM",
  },
  {
    id: "doc-1002",
    filename: "bol_1001.jpg",
    type: "bill_of_lading",
    status: "needs_review",
    uploadedAt: "2026-03-23 09:22 AM",
  },
];

export default function DriverUploadsPage() {
  const [selectedFile, setSelectedFile] = useState<string>("");

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Uploads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Upload Documents</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Upload rate confirmations, BOLs, invoices, and supporting files so the back office can
            process your load faster.
          </p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-950">New Upload</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Choose a file from your device. In V1 this is a UI placeholder and will be connected
              to the real upload API next.
            </p>

            <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
              <div className="text-sm font-medium text-slate-700">
                Drag and drop files here, or choose from device
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Supported examples: PDF, JPG, PNG
              </p>

              <label className="mt-5 inline-flex cursor-pointer rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Choose File
                <input
                  type="file"
                  className="hidden"
                  onChange={(event) =>
                    setSelectedFile(event.target.files?.[0]?.name ?? "")
                  }
                />
              </label>

              {selectedFile ? (
                <div className="mt-4 text-sm font-medium text-slate-900">
                  Selected: {selectedFile}
                </div>
              ) : null}
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Upload Document
              </button>
              <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
                Clear
              </button>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">Recent Uploads</h2>
              <div className="mt-4 space-y-3">
                {recentUploads.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-semibold text-slate-900">{item.filename}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.type}</div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          item.status === "processed"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {item.status.replace("_", " ")}
                      </span>
                      <span className="text-xs text-slate-500">{item.uploadedAt}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">Tips</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                <li>• Upload clear photos or PDFs whenever possible.</li>
                <li>• Include all pages for rate confirmations and invoices.</li>
                <li>• Make sure signatures are visible on delivery documents.</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}