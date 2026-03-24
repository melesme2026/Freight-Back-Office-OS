const servicePlans = [
  {
    id: "plan-starter",
    name: "Starter",
    code: "starter",
    billingCycle: "monthly",
    basePrice: "$99.00",
    perLoadPrice: "$5.00",
    perDriverPrice: "$2.00",
    isActive: true,
  },
  {
    id: "plan-growth",
    name: "Growth",
    code: "growth",
    billingCycle: "monthly",
    basePrice: "$199.00",
    perLoadPrice: "$4.00",
    perDriverPrice: "$1.50",
    isActive: true,
  },
  {
    id: "plan-pro",
    name: "Pro",
    code: "pro",
    billingCycle: "monthly",
    basePrice: "$399.00",
    perLoadPrice: "$3.00",
    perDriverPrice: "$1.00",
    isActive: false,
  },
];

export default function BillingPlansPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Billing / Plans</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Service Plans</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage pricing plans, billing cadence, and usage pricing for customer subscriptions.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Plan
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Plan</th>
                  <th className="px-5 py-4 font-semibold">Code</th>
                  <th className="px-5 py-4 font-semibold">Billing Cycle</th>
                  <th className="px-5 py-4 font-semibold">Base Price</th>
                  <th className="px-5 py-4 font-semibold">Per Load</th>
                  <th className="px-5 py-4 font-semibold">Per Driver</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {servicePlans.map((plan) => (
                  <tr key={plan.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{plan.name}</div>
                      <div className="text-xs text-slate-500">{plan.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{plan.code}</td>
                    <td className="px-5 py-4 text-slate-700">{plan.billingCycle}</td>
                    <td className="px-5 py-4 font-medium text-slate-900">{plan.basePrice}</td>
                    <td className="px-5 py-4 text-slate-700">{plan.perLoadPrice}</td>
                    <td className="px-5 py-4 text-slate-700">{plan.perDriverPrice}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                          plan.isActive
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {plan.isActive ? "active" : "inactive"}
                      </span>
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