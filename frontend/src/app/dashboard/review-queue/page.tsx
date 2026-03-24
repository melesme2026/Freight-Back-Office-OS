const reviewItems = [
  {
    id: "rq-1001",
    loadNumber: "LOAD-1001",
    issueCount: 2,
    primaryIssue: "Missing invoice",
    severity: "high",
    documentType: "bill_of_lading",
  },
  {
    id: "rq-1002",
    loadNumber: "LOAD-1005",
    issueCount: 1,
    primaryIssue: "Amount mismatch",
    severity: "medium",
    documentType: "invoice",
  },
  {
    id: "rq-1003",
    loadNumber: "LOAD-1010",
    issueCount: 3,
    primaryIssue: "Unreadable document",
    severity: "high",
    documentType: "rate_confirmation",
  },
];

function severityBadge(severity: string) {
  switch (severity) {
    case "high":
      return "bg-rose-100 text-rose-800";
    case "medium":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function ReviewQueuePage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Review Queue</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Review Queue</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Review loads that require human attention due to missing information, failed validation,
            or low-confidence extraction.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Items awaiting review</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">11</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">High severity</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">4</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Resolved today</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">6</div>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Queue Item</th>
                  <th className="px-5 py-4 font-semibold">Load</th>
                  <th className="px-5 py-4 font-semibold">Primary Issue</th>
                  <th className="px-5 py-4 font-semibold">Document Type</th>
                  <th className="px-5 py-4 font-semibold">Severity</th>
                  <th className="px-5 py-4 font-semibold">Issue Count</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reviewItems.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{item.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{item.loadNumber}</td>
                    <td className="px-5 py-4 text-slate-700">{item.primaryIssue}</td>
                    <td className="px-5 py-4 text-slate-700">{item.documentType}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${severityBadge(item.severity)}`}
                      >
                        {item.severity}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-900">{item.issueCount}</td>
                    <td className="px-5 py-4">
                      <button className="text-sm font-semibold text-brand-700 hover:text-brand-800">
                        Review →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}