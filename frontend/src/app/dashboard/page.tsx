import Link from "next/link";

const dashboardCards = [
  {
    title: "Loads",
    description: "Track active loads, missing documents, and lifecycle progress.",
    href: "/dashboard/loads",
  },
  {
    title: "Review Queue",
    description: "Resolve validation issues and correct extracted fields.",
    href: "/dashboard/review-queue",
  },
  {
    title: "Billing",
    description: "Review subscriptions, invoices, payments, and account status.",
    href: "/dashboard/billing",
  },
  {
    title: "Customers",
    description: "Manage customer accounts, onboarding, and operational readiness.",
    href: "/dashboard/customers",
  },
  {
    title: "Drivers",
    description: "View drivers, activity, and related paperwork readiness.",
    href: "/dashboard/drivers",
  },
  {
    title: "Support",
    description: "Monitor support tickets, escalations, and issue resolution.",
    href: "/dashboard/support",
  },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Operator Dashboard</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Freight Back Office OS
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Centralize load operations, paperwork review, onboarding, billing, and support in one
              workspace.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
            <div className="text-xs uppercase tracking-wide text-slate-500">Environment</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">Local / V1</div>
          </div>
        </header>

        <section className="mb-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Loads in progress</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">24</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Needs review</div>
            <div className="mt-2 text-3xl font-bold text-amber-600">7</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Open invoices</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">12</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Support tickets</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">3</div>
          </div>
        </section>

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {dashboardCards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-300"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">{card.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
                </div>
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                  Open
                </span>
              </div>
              <div className="mt-5 text-sm font-medium text-brand-700 group-hover:text-brand-800">
                Go to {card.title} →
              </div>
            </Link>
          ))}
        </section>
      </div>
    </main>
  );
}