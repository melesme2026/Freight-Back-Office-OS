import Link from "next/link";

type LoadDetailPageProps = {
  params: {
    loadId: string;
  };
};

export default function LoadDetailPage({ params }: LoadDetailPageProps) {
  const { loadId } = params;

  const load = {
    id: loadId,
    loadNumber: "LOAD-1001",
    status: "needs_review",
    driver: "Demo Driver",
    broker: "Alpha Logistics",
    customer: "Demo Customer Account",
    pickup: "Detroit, MI",
    delivery: "Columbus, OH",
    grossAmount: "$1,250.00",
    documents: [
      { name: "Rate Confirmation", status: "received" },
      { name: "Bill of Lading", status: "received" },
      { name: "Invoice", status: "missing" },
    ],
    validationIssues: [
      "Invoice missing",
      "Broker email not confirmed",
    ],
    timeline: [
      "Load created",
      "Rate confirmation uploaded",
      "BOL uploaded",
      "Validation flagged missing invoice",
    ],
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {load.loadNumber}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Full operational view of a load, including documents, validation issues, and workflow
              progress.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Mark Reviewed
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              Advance Status
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">Load Summary</h2>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                  {load.status.replace("_", " ")}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Driver</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.driver}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Broker</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.broker}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.customer}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Gross Amount</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.grossAmount}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Pickup</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.pickup}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Delivery</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{load.delivery}</div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Documents</h2>
              <div className="space-y-3">
                {load.documents.map((document) => (
                  <div
                    key={document.name}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div>
                      <div className="text-sm font-medium text-slate-900">{document.name}</div>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        document.status === "received"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {document.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Validation Issues</h2>
              <div className="space-y-3">
                {load.validationIssues.map((issue) => (
                  <div
                    key={issue}
                    className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                  >
                    {issue}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Timeline</h2>
              <ol className="space-y-3">
                {load.timeline.map((item, index) => (
                  <li key={item} className="flex gap-3">
                    <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                      {index + 1}
                    </div>
                    <div className="text-sm text-slate-700">{item}</div>
                  </li>
                ))}
              </ol>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <Link
                  href="/dashboard/review-queue"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Open Review Queue
                </Link>
                <Link
                  href="/dashboard/documents/document-1001"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  View Related Documents
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}