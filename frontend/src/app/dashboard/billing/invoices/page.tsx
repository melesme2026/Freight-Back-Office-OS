import Link from "next/link";

const invoices = [
  {
    id: "inv-1001",
    invoiceNumber: "INV-1001",
    customer: "Demo Customer Account",
    status: "open",
    totalAmount: "$449.00",
    amountDue: "$449.00",
    issuedAt: "2026-03-20",
    dueAt: "2026-03-30",
  },
  {
    id: "inv-1002",
    invoiceNumber: "INV-1002",
    customer: "North Route Logistics",
    status: "paid",
    totalAmount: "$799.00",
    amountDue: "$0.00",
    issuedAt: "2026-03-15",
    dueAt: "2026-03-25",
  },
  {
    id: "inv-1003",
    invoiceNumber: "INV-1003",
    customer: "Metro Freight Group",
    status: "past_due",
    totalAmount: "$299.00",
    amountDue: "$299.00",
    issuedAt: "2026-03-10",
    dueAt: "2026-03-20",
  },
];

function statusBadge(status: string) {
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

export default function BillingInvoicesPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Invoices</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Invoices</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review issued invoices, open balances, due dates, and customer billing status.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Invoice
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Invoice</th>
                  <th className="px-5 py-4 font-semibold">Customer</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Total</th>
                  <th className="px-5 py-4 font-semibold">Amount Due</th>
                  <th className="px-5 py-4 font-semibold">Issued</th>
                  <th className="px-5 py-4 font-semibold">Due</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{invoice.invoiceNumber}</div>
                      <div className="text-xs text-slate-500">{invoice.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{invoice.customer}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(invoice.status)}`}
                      >
                        {invoice.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-900">{invoice.totalAmount}</td>
                    <td className="px-5 py-4 text-slate-700">{invoice.amountDue}</td>
                    <td className="px-5 py-4 text-slate-700">{invoice.issuedAt}</td>
                    <td className="px-5 py-4 text-slate-700">{invoice.dueAt}</td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/dashboard/billing/invoices/${invoice.id}`}
                        className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}