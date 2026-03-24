import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col justify-center px-6 py-16">
        <div className="max-w-3xl">
          <div className="mb-6 inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 shadow-sm">
            Freight Back Office OS V1
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            Run freight paperwork, load tracking, review, and billing from one system.
          </h1>

          <p className="mt-5 text-lg leading-8 text-slate-600">
            Freight Back Office OS is a document-driven operating system for small and growing
            trucking businesses. It brings together load lifecycle tracking, document intake,
            validation, billing, onboarding, and support in one workflow.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/dashboard"
              className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700"
            >
              Open Dashboard
            </Link>

            <Link
              href="/driver-portal"
              className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Open Driver Portal
            </Link>
          </div>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-3">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">Document-first workflow</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Track rate confirmations, BOLs, invoices, and supporting files from intake through
              review and validation.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">Operational visibility</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              See where each load stands, what is missing, what needs review, and what is ready to
              move forward.
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-slate-900">Billing foundation</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage subscriptions, invoices, payments, and internal financial tracking as the
              platform grows into SaaS.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}