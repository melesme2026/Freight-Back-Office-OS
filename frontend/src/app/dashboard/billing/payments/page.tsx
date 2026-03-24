const payments = [
  {
    id: "pay-1001",
    customer: "Demo Customer Account",
    invoiceNumber: "INV-1001",
    provider: "manual",
    status: "succeeded",
    amount: "$200.00",
    attemptedAt: "2026-03-23 09:15 AM",
  },
  {
    id: "pay-1002",
    customer: "North Route Logistics",
    invoiceNumber: "INV-1002",
    provider: "stripe",
    status: "succeeded",
    amount: "$799.00",
    attemptedAt: "2026-03-23 10:05 AM",
  },
  {
    id: "pay-1003",
    customer: "Metro Freight Group",
    invoiceNumber: "INV-1003",
    provider: "stripe",
    status: "failed",
    amount: "$299.00",
    attemptedAt: "2026-03-23 11:40 AM",
  },
];

function statusBadge(status: string) {
  switch (status) {
    case "succeeded":
      return "bg-emerald-100 text-emerald-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    case "pending":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function BillingPaymentsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Payments</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Payments</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review payment attempts, success and failure states, invoice linkage, and collected
              amounts.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            Record Payment
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Payment</th>
                  <th className="px-5 py-4 font-semibold">Customer</th>
                  <th className="px-5 py-4 font-semibold">Invoice</th>
                  <th className="px-5 py-4 font-semibold">Provider</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Amount</th>
                  <th className="px-5 py-4 font-semibold">Attempted At</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {payments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{payment.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{payment.customer}</td>
                    <td className="px-5 py-4 text-slate-700">{payment.invoiceNumber}</td>
                    <td className="px-5 py-4 text-slate-700">{payment.provider}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(payment.status)}`}
                      >
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-900">{payment.amount}</td>
                    <td className="px-5 py-4 text-slate-700">{payment.attemptedAt}</td>
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