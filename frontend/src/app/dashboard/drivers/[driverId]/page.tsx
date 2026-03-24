import Link from "next/link";

type DriverDetailPageProps = {
  params: {
    driverId: string;
  };
};

export default function DriverDetailPage({ params }: DriverDetailPageProps) {
  const { driverId } = params;

  const driver = {
    id: driverId,
    name: "Demo Driver",
    phone: "+1 (586) 555-0101",
    email: "driver@demo-freight.com",
    status: "active",
    customer: "Demo Customer Account",
    recentLoads: [
      { id: "load-1001", loadNumber: "LOAD-1001", status: "needs_review" },
      { id: "load-1002", loadNumber: "LOAD-1002", status: "validated" },
      { id: "load-1003", loadNumber: "LOAD-1003", status: "submitted" },
    ],
    notes:
      "Primary driver used for early workflow validation. Frequently submits paperwork through mobile-first channels.",
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Drivers / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">{driver.name}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Driver profile, contact details, related loads, and operational context.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Edit Driver
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              New Load
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">Driver Summary</h2>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                  {driver.status}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Phone</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{driver.phone}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Email</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{driver.email}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{driver.customer}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Driver ID</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{driver.id}</div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Recent Loads</h2>
              <div className="space-y-3">
                {driver.recentLoads.map((load) => (
                  <Link
                    key={load.id}
                    href={`/dashboard/loads/${load.id}`}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                  >
                    <div>
                      <div className="text-sm font-medium text-slate-900">{load.loadNumber}</div>
                      <div className="text-xs text-slate-500">{load.id}</div>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        load.status === "needs_review"
                          ? "bg-amber-100 text-amber-800"
                          : load.status === "validated"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {load.status.replace("_", " ")}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Operational Notes</h2>
              <p className="text-sm leading-6 text-slate-600">{driver.notes}</p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <Link
                  href="/dashboard/loads"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  View All Loads
                </Link>
                <Link
                  href="/dashboard/support"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Open Support
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}