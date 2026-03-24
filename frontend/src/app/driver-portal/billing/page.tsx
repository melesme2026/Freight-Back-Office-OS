import Link from "next/link";

const summary = [
  { label: "Open Invoices", value: "2" },
  { label: "Paid Invoices", value: "5" },
  { label: "Pending Payments", value: "1" },
  { label: "Total Due", value: "$449.00" },
];

const recentInvoices = [
  {
    id: "inv-1001",
    invoiceNumber: "INV-1001",
    status: "open",
    totalAmount: "$449.00",
    dueAt: "2026-03-30",
  },
  {
    id: "inv-1002",
    invoiceNumber: "INV-1002",
    status: "paid",
    totalAmount: "$299.00",
    dueAt: "2026-03-21",
  },
];

function badgeClass(status: string) {
  switch (status) {
    case "paid":
      return "bg-emerald-100 text-emerald-800";
    case "open":
      return "bg-blue-100 text-blue-800";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function DriverBillingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">Driver Portal / Billing</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing Overview</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Review invoice status, payment progress, and the current amount still outstanding.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          {summary.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft"
            >
              <div className="text-sm text-slate-500">{item.label}</div>
              <div className="mt-2 text-3xl font-bold text-slate-950">{item.value}</div>
            </div>
          ))}
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.3fr,1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-950">Recent Invoices</h2>
              <Link
                href="/driver-portal/billing/invoices"
                className="text-sm font-semibold text-brand-700 hover:text-brand-800"
              >
                View all →
              </Link>
            </div>

            <div className="space-y-3">
              {recentInvoices.map((invoice) => (
                <Link
                  key={invoice.id}
                  href="/driver-portal/billing/invoices"
                  className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{invoice.invoiceNumber}</div>
                    <div className="text-xs text-slate-500">Due: {invoice.dueAt}</div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-900">{invoice.totalAmount}</span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeClass(invoice.status)}`}
                    >
                      {invoice.status.replace("_", " ")}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Billing Areas</h2>
              <div className="space-y-3">
                <Link
                  href="/driver-portal/billing/invoices"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Invoices
                </Link>
                <Link
                  href="/driver-portal/billing/payments"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Payments
                </Link>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">V1 note</h2>
              <p className="text-sm leading-6 text-slate-600">
                Driver billing views are intentionally simple in V1 and focus on visibility first.
                Advanced payout and factoring automation can be layered in after real workflow
                validation.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}