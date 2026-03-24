const onboardingAccounts = [
  {
    id: "cust-1001",
    accountName: "Demo Customer Account",
    status: "in_progress",
    documentsReceived: true,
    pricingConfirmed: true,
    paymentMethodAdded: false,
    driversCreated: true,
    channelConnected: false,
    goLiveReady: false,
  },
  {
    id: "cust-1002",
    accountName: "North Route Logistics",
    status: "ready",
    documentsReceived: true,
    pricingConfirmed: true,
    paymentMethodAdded: true,
    driversCreated: true,
    channelConnected: true,
    goLiveReady: true,
  },
  {
    id: "cust-1003",
    accountName: "Metro Freight Group",
    status: "not_started",
    documentsReceived: false,
    pricingConfirmed: false,
    paymentMethodAdded: false,
    driversCreated: false,
    channelConnected: false,
    goLiveReady: false,
  },
];

function badgeClass(status: string) {
  switch (status) {
    case "ready":
      return "bg-emerald-100 text-emerald-800";
    case "in_progress":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function checkmark(value: boolean) {
  return value ? "Yes" : "No";
}

export default function OnboardingPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Onboarding</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Onboarding</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Track customer readiness, onboarding checklist completion, payment setup, and go-live
              status.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Customer
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Accounts in onboarding</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">9</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Ready to go live</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">3</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Missing payment setup</div>
            <div className="mt-2 text-3xl font-bold text-amber-700">4</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Channel not connected</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">2</div>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Customer</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Docs</th>
                  <th className="px-5 py-4 font-semibold">Pricing</th>
                  <th className="px-5 py-4 font-semibold">Payment</th>
                  <th className="px-5 py-4 font-semibold">Drivers</th>
                  <th className="px-5 py-4 font-semibold">Channel</th>
                  <th className="px-5 py-4 font-semibold">Go Live</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {onboardingAccounts.map((account) => (
                  <tr key={account.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{account.accountName}</div>
                      <div className="text-xs text-slate-500">{account.id}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badgeClass(account.status)}`}
                      >
                        {account.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.documentsReceived)}</td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.pricingConfirmed)}</td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.paymentMethodAdded)}</td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.driversCreated)}</td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.channelConnected)}</td>
                    <td className="px-5 py-4 text-slate-700">{checkmark(account.goLiveReady)}</td>
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