import Link from "next/link";

const loads = [
  {
    id: "load-1001",
    loadNumber: "LOAD-1001",
    driver: "Demo Driver",
    broker: "Alpha Logistics",
    status: "needs_review",
    documents: "Rate Con, BOL",
    amount: "$1,250.00",
  },
  {
    id: "load-1002",
    loadNumber: "LOAD-1002",
    driver: "Sam Haile",
    broker: "North Peak Freight",
    status: "validated",
    documents: "Rate Con, BOL, Invoice",
    amount: "$980.00",
  },
  {
    id: "load-1003",
    loadNumber: "LOAD-1003",
    driver: "Daniel Tes",
    broker: "Metro Carrier Group",
    status: "submitted",
    documents: "Complete",
    amount: "$1,540.00",
  },
];

function statusBadge(status: string) {
  switch (status) {
    case "needs_review":
      return "bg-amber-100 text-amber-800";
    case "validated":
      return "bg-emerald-100 text-emerald-800";
    case "submitted":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function LoadsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Loads</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Loads</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review active freight loads, document completeness, and current workflow state.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Filter
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              New Load
            </button>
          </div>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Load</th>
                  <th className="px-5 py-4 font-semibold">Driver</th>
                  <th className="px-5 py-4 font-semibold">Broker</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Documents</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {loads.map((load) => (
                  <tr key={load.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{load.loadNumber}</div>
                      <div className="text-xs text-slate-500">{load.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{load.driver}</td>
                    <td className="px-5 py-4 text-slate-700">{load.broker}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(load.status)}`}
                      >
                        {load.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{load.documents}</td>
                    <td className="px-5 py-4 font-medium text-slate-900">{load.amount}</td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/dashboard/loads/${load.id}`}
                        className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                      >
                        View →
                      </Link>
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