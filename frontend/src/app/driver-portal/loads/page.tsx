const loadSections = [
  {
    title: "Active Loads",
    description:
      "Driver-facing active and recent load visibility will appear here once the driver portal is wired to live load assignment data.",
    status: "Planned after V1",
  },
  {
    title: "Document Progress",
    description:
      "Drivers will be able to see paperwork readiness, missing documents, and review blockers after release-safe portal integration is complete.",
    status: "Planned after V1",
  },
  {
    title: "Load Status and Earnings",
    description:
      "Load lifecycle status and payout-related amounts should only be shown after the driver portal is connected to real scoped load and billing data.",
    status: "Planned after V1",
  },
] as const;

export default function DriverLoadsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Loads</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">My Loads</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Load visibility in the driver portal is intentionally lightweight in V1 to avoid
            showing hardcoded operational records or unsupported live status and payout data.
          </p>
        </div>

        <section className="grid gap-5 md:grid-cols-3">
          {loadSections.map((section) => (
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

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Live load numbers, brokers, routes, review state, validation state, submitted status,
            and payout-related amounts should only be shown after the driver portal is connected to
            real session-scoped load endpoints with proper response normalization and access control.
          </p>
        </section>
      </div>
    </main>
  );
}