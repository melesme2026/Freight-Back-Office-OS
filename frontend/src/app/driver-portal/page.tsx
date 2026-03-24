import Link from "next/link";

const quickStats = [
  { label: "Open Loads", value: "4" },
  { label: "Pending Uploads", value: "2" },
  { label: "Invoices", value: "3" },
  { label: "Support Tickets", value: "1" },
];

export default function DriverPortalPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">
            Driver Workspace
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Upload paperwork, view loads, review invoice and payment status, and open support
            requests without needing the full operator dashboard.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          {quickStats.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
            >
              <div className="text-sm text-slate-500">{item.label}</div>
              <div className="mt-2 text-3xl font-bold text-slate-950">{item.value}</div>
            </div>
          ))}
        </section>

        <section className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          <Link
            href="/driver-portal/uploads"
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
          >
            <h2 className="text-lg font-semibold text-slate-950">Uploads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Send rate cons, BOLs, invoices, and supporting paperwork.
            </p>
          </Link>

          <Link
            href="/driver-portal/loads"
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
          >
            <h2 className="text-lg font-semibold text-slate-950">Loads</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              View your active and recent freight loads and related document status.
            </p>
          </Link>

          <Link
            href="/driver-portal/billing"
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
          >
            <h2 className="text-lg font-semibold text-slate-950">Billing</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review invoices, payment progress, and billing-related updates.
            </p>
          </Link>

          <Link
            href="/driver-portal/support"
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
          >
            <h2 className="text-lg font-semibold text-slate-950">Support</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Open tickets and follow operational or billing issues.
            </p>
          </Link>
        </section>
      </div>
    </main>
  );
}