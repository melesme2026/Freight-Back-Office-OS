type DocumentDetailPageProps = {
  params: {
    documentId: string;
  };
};

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const { documentId } = params;

  const document = {
    id: documentId,
    originalFilename: "rate_confirmation_1001.pdf",
    documentType: "rate_confirmation",
    processingStatus: "completed",
    sourceChannel: "manual",
    linkedLoad: "LOAD-1001",
    uploadedBy: "Demo Admin",
    uploadedAt: "2026-03-23 09:10 AM",
    classificationConfidence: "0.97",
    extractedFields: [
      { field: "load_number", value: "LOAD-1001", confidence: "0.99" },
      { field: "broker_name", value: "Alpha Logistics", confidence: "0.95" },
      { field: "gross_amount", value: "$1,250.00", confidence: "0.93" },
      { field: "pickup_date", value: "2026-03-24", confidence: "0.91" },
    ],
    validationIssues: ["Broker email missing"],
    previewText:
      "RATE CONFIRMATION\nLoad Number: LOAD-1001\nBroker: Alpha Logistics\nTotal Rate: $1,250.00\nPickup Date: 2026-03-24",
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Documents / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {document.originalFilename}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review document metadata, extracted fields, validation outcomes, and preview content.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Reprocess
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              Link to Load
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">Document Summary</h2>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                  {document.processingStatus}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Document Type</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.documentType}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Source Channel</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.sourceChannel}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Linked Load</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.linkedLoad}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Classification Confidence
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.classificationConfidence}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Uploaded By</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.uploadedBy}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Uploaded At</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {document.uploadedAt}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Extracted Fields</h2>
              <div className="space-y-3">
                {document.extractedFields.map((field) => (
                  <div
                    key={field.field}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-500">
                        {field.field}
                      </div>
                      <div className="mt-1 text-sm font-medium text-slate-900">
                        {field.value}
                      </div>
                    </div>
                    <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                      {field.confidence}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Preview</h2>
              <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">
                {document.previewText}
              </pre>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Validation Issues</h2>
              <div className="space-y-3">
                {document.validationIssues.map((issue) => (
                  <div
                    key={issue}
                    className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                  >
                    {issue}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Correct Extracted Fields
                </button>
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Resolve Validation Issue
                </button>
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Download Original File
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}