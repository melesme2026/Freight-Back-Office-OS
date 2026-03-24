const payments = [
  {
    id: "pay-1001",
    invoiceNumber: "INV-1001",
    provider: "manual",
    status: "succeeded",
    amount: "$200.00",
    attemptedAt: "2026-03-23 09:15 AM",
  },
  {
    id: "pay-1002",
    invoiceNumber: "INV-1002",
    provider: "stripe",
    status: "succeeded",
    amount: "$299.00",
    attemptedAt: "2026-03-21 01:40 PM",
  },
  {
    id: "pay-1003",
    invoiceNumber: "INV-1003",
    provider: "stripe",
    status: "failed",
    amount: "$180.00",
    attemptedAt: "2026-03-22 11:10 AM",
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

export default function DriverBillingPaymentsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-medium text-brand-700">
            Driver Portal / Billing / Payments
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Payments</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Review recorded payment attempts, statuses, and the invoices they were applied to.
          </p>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Payment</th>
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