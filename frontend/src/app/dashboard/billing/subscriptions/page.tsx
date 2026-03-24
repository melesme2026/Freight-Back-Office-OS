const subscriptions = [
  {
    id: "sub-1001",
    customer: "Demo Customer Account",
    plan: "Starter",
    status: "active",
    billingEmail: "billing@demo-freight.com",
    currentPeriodStart: "2026-03-01",
    currentPeriodEnd: "2026-03-31",
    cancelAtPeriodEnd: false,
  },
  {
    id: "sub-1002",
    customer: "North Route Logistics",
    plan: "Growth",
    status: "active",
    billingEmail: "billing@northroutelogistics.com",
    currentPeriodStart: "2026-03-01",
    currentPeriodEnd: "2026-03-31",
    cancelAtPeriodEnd: false,
  },
  {
    id: "sub-1003",
    customer: "Metro Freight Group",
    plan: "Starter",
    status: "cancelled",
    billingEmail: "finance@metrofreightgroup.com",
    currentPeriodStart: "2026-02-01",
    currentPeriodEnd: "2026-02-28",
    cancelAtPeriodEnd: true,
  },
];

function statusBadge(status: string) {
  switch (status) {
    case "active":
      return "bg-emerald-100 text-emerald-800";
    case "cancelled":
      return "bg-slate-200 text-slate-700";
    case "past_due":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function BillingSubscriptionsPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Billing / Subscriptions
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Subscriptions</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Review active customer subscriptions, billing periods, plan assignments, and account
              billing status.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Subscription
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Subscription</th>
                  <th className="px-5 py-4 font-semibold">Customer</th>
                  <th className="px-5 py-4 font-semibold">Plan</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Billing Email</th>
                  <th className="px-5 py-4 font-semibold">Current Period</th>
                  <th className="px-5 py-4 font-semibold">Cancel at Period End</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {subscriptions.map((subscription) => (
                  <tr key={subscription.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{subscription.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{subscription.customer}</td>
                    <td className="px-5 py-4 text-slate-700">{subscription.plan}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(subscription.status)}`}
                      >
                        {subscription.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{subscription.billingEmail}</td>
                    <td className="px-5 py-4 text-slate-700">
                      {subscription.currentPeriodStart} → {subscription.currentPeriodEnd}
                    </td>
                    <td className="px-5 py-4 text-slate-700">
                      {subscription.cancelAtPeriodEnd ? "Yes" : "No"}
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