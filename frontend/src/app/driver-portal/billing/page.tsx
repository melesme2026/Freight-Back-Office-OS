import Link from "next/link";

const billingSections = [
  {
    title: "Invoices",
    description:
      "Review invoice history, due balances, and invoice-level detail once live driver billing data is wired.",
    href: "/driver-portal/billing/invoices",
    status: "Planned after V1",
  },
  {
    title: "Payments",
    description:
      "Review payment attempts, transaction outcomes, and applied invoice payments after billing integration is release-ready.",
    href: "/driver-portal/billing/payments",
    status: "Planned after V1",
  },
] as const;

export default function DriverBillingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing Overview</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Billing visibility in the driver portal is intentionally lightweight in V1 to avoid
            showing hardcoded financial totals or unsupported invoice and payment state.
          </p>
        </div>

        <section className="grid gap-5 md:grid-cols-2">
          {billingSections.map((section) => (
            <div
              key={section.title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">{section.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{section.description}</p>
                </div>
                <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                  {section.status}
                </span>
              </div>

              <div className="mt-5">
                <Link
                  href={section.href}
                  className="inline-flex rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open {section.title}
                </Link>
              </div>
            </div>
          ))}
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">V1 note</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Live invoice counts, paid totals, pending payments, total due, and recent billing
            activity should only be shown after the driver portal is connected to real billing
            endpoints with proper session-scoped access control and response normalization.
          </p>
        </section>
      </div>
    </main>
  );
}