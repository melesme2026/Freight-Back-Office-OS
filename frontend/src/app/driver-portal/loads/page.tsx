const driverLoads = [
  {
    id: "load-1001",
    loadNumber: "LOAD-1001",
    broker: "Alpha Logistics",
    route: "Detroit, MI → Columbus, OH",
    status: "needs_review",
    amount: "$1,250.00",
  },
  {
    id: "load-1002",
    loadNumber: "LOAD-1002",
    broker: "North Peak Freight",
    route: "Toledo, OH → Louisville, KY",
    status: "validated",
    amount: "$980.00",
  },
  {
    id: "load-1003",
    loadNumber: "LOAD-1003",
    broker: "Metro Carrier Group",
    route: "Chicago, IL → Indianapolis, IN",
    status: "submitted",
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

export default function DriverLoadsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Loads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">My Loads</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            See your recent and active loads, track document progress, and understand what still
            needs attention before billing or payout can move forward.
          </p>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Load</th>
                  <th className="px-5 py-4 font-semibold">Broker</th>
                  <th className="px-5 py-4 font-semibold">Route</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {driverLoads.map((load) => (
                  <tr key={load.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{load.loadNumber}</div>
                      <div className="text-xs text-slate-500">{load.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{load.broker}</td>
                    <td className="px-5 py-4 text-slate-700">{load.route}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(load.status)}`}
                      >
                        {load.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-900">{load.amount}</td>
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