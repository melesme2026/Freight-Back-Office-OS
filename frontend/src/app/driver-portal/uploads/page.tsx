const uploadSections = [
  {
    title: "Document Upload",
    description:
      "Driver document upload will appear here once the driver portal is wired to the real upload API and storage flow.",
    status: "Planned after V1",
  },
  {
    title: "Recent Uploads",
    description:
      "Recent uploaded files and processing status will be shown here after live upload tracking is connected to backend storage and document processing.",
    status: "Planned after V1",
  },
  {
    title: "Upload Guidance",
    description:
      "Drivers should upload clear PDFs or photos with complete pages and visible signatures when document submission becomes live.",
    status: "Ready for rollout",
  },
] as const;

const uploadTips = [
  "Upload clear photos or PDFs whenever possible.",
  "Include all pages for rate confirmations and invoices.",
  "Make sure signatures are visible on delivery documents.",
] as const;

export default function DriverUploadsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Uploads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Upload Documents</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Document upload in the driver portal is intentionally lightweight in V1 to avoid
            showing unsupported upload actions, fake processing state, or hardcoded recent files.
          </p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr,1fr]">
          <section className="grid gap-5">
            {uploadSections.map((section) => (
              <div
                key={section.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <h2 className="text-lg font-semibold text-slate-950">{section.title}</h2>
                  <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    {section.status}
                  </span>
                </div>

                <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
              </div>
            ))}
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">Tips</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                {uploadTips.map((tip) => (
                  <li key={tip}>• {tip}</li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Live file selection, upload submission, recent upload history, processing results,
                and document statuses should only be shown after the driver portal is connected to
                real upload endpoints, storage, and session-scoped document APIs.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}