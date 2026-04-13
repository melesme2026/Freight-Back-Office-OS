export default function DriverBillingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Driver-scoped billing list APIs are not available yet. Current billing endpoints are
            organization/customer scoped and do not provide a dedicated driver portal view.
          </p>
        </div>

        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-slate-950">Current support in V1</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>• Driver portal can preview loads and support by driver ID.</li>
            <li>• Driver portal can upload documents through the live upload endpoint.</li>
            <li>• Driver billing statements and payment history remain unsupported.</li>
          </ul>
        </section>
      </div>
    </main>
  );
}
