import Link from "next/link";

const billingSummary = [
  { label: "Active Subscriptions", value: "6" },
  { label: "Open Invoices", value: "12" },
  { label: "Past Due", value: "3" },
  { label: "Collected This Month", value: "$4,820.00" },
];

const recentInvoices = [
  {
    id: "inv-1001",
    invoiceNumber: "INV-1001",
    customer: "Demo Customer Account",
    total: "$449.00",
    status: "open",
  },
  {
    id: "inv-1002",
    invoiceNumber: "INV-1002",
    customer: "North Route Logistics",
    total: "$799.00",
    status: "paid",
  },
  {
    id: "inv-1003",
    invoiceNumber: "INV-1003",
    customer: "Metro Freight Group",
    total: "$299.00",
    status: "past_due",
  },
];

function invoiceBadge(status: string) {
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

export default function BillingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Billing</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review subscription performance, invoice status, payment activity, and account
              revenue signals.
            </p>
          </div>

          <div className="flex gap-3">
            <Link
              href="/dashboard/billing/plans"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              Plans
            </Link>
            <Link
              href="/dashboard/billing/invoices"
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Invoices
            </Link>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          {billingSummary.map((item) => (
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
                href="/dashboard/billing/invoices"
                className="text-sm font-semibold text-brand-700 hover:text-brand-800"
              >
                View all →
              </Link>
            </div>

            <div className="space-y-3">
              {recentInvoices.map((invoice) => (
                <Link
                  key={invoice.id}
                  href={`/dashboard/billing/invoices/${invoice.id}`}
                  className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{invoice.invoiceNumber}</div>
                    <div className="text-xs text-slate-500">{invoice.customer}</div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-900">{invoice.total}</span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${invoiceBadge(invoice.status)}`}
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
                  href="/dashboard/billing/plans"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Service Plans
                </Link>
                <Link
                  href="/dashboard/billing/subscriptions"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Subscriptions
                </Link>
                <Link
                  href="/dashboard/billing/invoices"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Invoices
                </Link>
                <Link
                  href="/dashboard/billing/payments"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Payments
                </Link>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Notes</h2>
              <p className="text-sm leading-6 text-slate-600">
                V1 billing is focused on subscription structure, invoice generation, payment
                tracking, and internal financial visibility. Advanced tax, discount, and refund
                workflows will follow later.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}