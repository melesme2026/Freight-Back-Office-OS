const supportSections = [
  {
    title: "Operational Tickets",
    description:
      "Track load exceptions, document follow-up, and workflow blockers once support queue APIs are wired.",
    status: "Planned after V1",
  },
  {
    title: "Billing Escalations",
    description:
      "Centralize invoice disputes, payment retry follow-up, and customer billing support workflows.",
    status: "Planned after V1",
  },
  {
    title: "Customer Support",
    description:
      "Review customer account issues, contact corrections, and organization-level support actions.",
    status: "Planned after V1",
  },
  {
    title: "Escalation Management",
    description:
      "Coordinate escalations across operations, finance, and back-office review teams.",
    status: "Planned after V1",
  },
] as const;

export default function SupportPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Dashboard / Support</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Support</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Support workflows are intentionally kept lightweight in V1 to avoid shipping fake
            operational data or unsupported ticket actions before backend support modules are live.
          </p>
        </div>

        <section className="grid gap-5 md:grid-cols-2">
          {supportSections.map((section) => (
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
            Core operational work for V1 should continue through the live dashboard modules already
            backed by the backend, including Loads, Review Queue, Billing, Customers, Drivers, and
            Documents. Dedicated support ticketing can be introduced after the underlying API,
            persistence, and assignment flows are release-ready.
          </p>
        </section>
      </div>
    </main>
  );
}