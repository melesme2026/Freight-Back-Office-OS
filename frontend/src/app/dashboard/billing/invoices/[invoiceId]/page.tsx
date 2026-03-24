type InvoiceDetailPageProps = {
  params: {
    invoiceId: string;
  };
};

export default function InvoiceDetailPage({ params }: InvoiceDetailPageProps) {
  const { invoiceId } = params;

  const invoice = {
    id: invoiceId,
    invoiceNumber: "INV-1001",
    customer: "Demo Customer Account",
    status: "open",
    currencyCode: "USD",
    subtotalAmount: "$449.00",
    taxAmount: "$0.00",
    totalAmount: "$449.00",
    amountPaid: "$0.00",
    amountDue: "$449.00",
    issuedAt: "2026-03-20",
    dueAt: "2026-03-30",
    billingPeriodStart: "2026-03-01",
    billingPeriodEnd: "2026-03-31",
    notes: "Monthly platform fee plus load usage charges.",
    lines: [
      {
        id: "line-1001",
        lineType: "subscription",
        description: "Starter monthly subscription",
        quantity: "1",
        unitPrice: "$99.00",
        lineTotal: "$99.00",
      },
      {
        id: "line-1002",
        lineType: "usage",
        description: "Per-load charges",
        quantity: "70",
        unitPrice: "$5.00",
        lineTotal: "$350.00",
      },
    ],
  };

  const statusBadge =
    invoice.status === "paid"
      ? "bg-emerald-100 text-emerald-800"
      : invoice.status === "past_due"
        ? "bg-rose-100 text-rose-800"
        : "bg-blue-100 text-blue-800";

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Billing / Invoices / Detail
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {invoice.invoiceNumber}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Invoice detail including totals, billing period, line items, and payment readiness.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Mark Paid
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              Collect Payment
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">Invoice Summary</h2>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge}`}>
                  {invoice.status.replace("_", " ")}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{invoice.customer}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Currency</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {invoice.currencyCode}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Issued At</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{invoice.issuedAt}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Due At</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{invoice.dueAt}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    Billing Period
                  </div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {invoice.billingPeriodStart} → {invoice.billingPeriodEnd}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Invoice ID</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{invoice.id}</div>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-500">Notes</div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{invoice.notes}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Invoice Lines</h2>
              <div className="space-y-3">
                {invoice.lines.map((line) => (
                  <div
                    key={line.id}
                    className="rounded-xl border border-slate-200 px-4 py-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">
                          {line.description}
                        </div>
                        <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                          {line.lineType}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-sm font-semibold text-slate-900">
                          {line.lineTotal}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {line.quantity} × {line.unitPrice}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Totals</h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Subtotal</span>
                  <span className="font-semibold text-slate-900">{invoice.subtotalAmount}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Tax</span>
                  <span className="font-semibold text-slate-900">{invoice.taxAmount}</span>
                </div>
                <div className="flex items-center justify-between border-t border-slate-200 pt-3">
                  <span className="text-slate-700">Total</span>
                  <span className="text-lg font-bold text-slate-950">{invoice.totalAmount}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Amount Paid</span>
                  <span className="font-semibold text-slate-900">{invoice.amountPaid}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Amount Due</span>
                  <span className="font-semibold text-rose-700">{invoice.amountDue}</span>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Record Manual Payment
                </button>
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Mark Past Due
                </button>
                <button className="w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-100">
                  Download Invoice
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}