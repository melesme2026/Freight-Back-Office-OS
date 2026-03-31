const billingSections = [
  {
    title: "Invoice History",
    description:
      "Driver-facing invoice history will appear here once the driver portal billing API is wired to live invoice records.",
    status: "Planned after V1",
  },
  {
    title: "Outstanding Balances",
    description:
      "Open balances, due dates, and payment follow-up will be shown here when live billing data is available.",
    status: "Planned after V1",
  },
  {
    title: "Payment Status",
    description:
      "Drivers will be able to review paid, open, and past-due invoice states after release-safe billing integration is complete.",
    status: "Planned after V1",
  },
] as const;

export default function DriverBillingInvoicesPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">
            Driver Portal / Billing / Invoices
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Invoices</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Billing visibility in the driver portal is intentionally lightweight in V1 to avoid
            showing hardcoded invoice data or unsupported payment state.
          </p>
        </div>

        <section className="grid gap-5 md:grid-cols-3">
          {billingSections.map((section) => (
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
            Live invoice totals, amount due, issued dates, and due dates should only be shown after
            the driver portal is connected to real billing endpoints with proper session-scoped
            access control and response normalization.
          </p>
        </section>
      </div>
    </main>
  );
}