import Link from "next/link";

type CustomerDetailPageProps = {
  params: {
    customerId: string;
  };
};

export default function CustomerDetailPage({ params }: CustomerDetailPageProps) {
  const { customerId } = params;

  const customer = {
    id: customerId,
    accountName: "Demo Customer Account",
    accountCode: "DEMO-001",
    status: "active",
    primaryContactName: "Demo Dispatcher",
    primaryContactEmail: "dispatch@demo-freight.com",
    primaryContactPhone: "+1 (586) 555-0100",
    billingEmail: "billing@demo-freight.com",
    notes:
      "Early pilot customer account used to validate V1 document intake, load workflow, and billing readiness.",
    onboarding: {
      documentsReceived: true,
      pricingConfirmed: true,
      paymentMethodAdded: false,
      driversCreated: true,
      channelConnected: true,
      goLiveReady: false,
    },
    recentLoads: [
      { id: "load-1001", loadNumber: "LOAD-1001", status: "needs_review", amount: "$1,250.00" },
      { id: "load-1002", loadNumber: "LOAD-1002", status: "validated", amount: "$980.00" },
      { id: "load-1003", loadNumber: "LOAD-1003", status: "submitted", amount: "$1,540.00" },
    ],
  };

  const readinessItems = [
    ["Documents Received", customer.onboarding.documentsReceived],
    ["Pricing Confirmed", customer.onboarding.pricingConfirmed],
    ["Payment Method Added", customer.onboarding.paymentMethodAdded],
    ["Drivers Created", customer.onboarding.driversCreated],
    ["Channel Connected", customer.onboarding.channelConnected],
    ["Go Live Ready", customer.onboarding.goLiveReady],
  ];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Customers / Detail</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {customer.accountName}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Customer account detail including contacts, onboarding readiness, and recent load
              activity.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Edit Account
            </button>
            <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              Add Subscription
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-950">Account Summary</h2>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                  {customer.status}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Account Code</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{customer.accountCode}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Customer ID</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{customer.id}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Primary Contact</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.primaryContactName}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Contact Email</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.primaryContactEmail}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Contact Phone</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">
                    {customer.primaryContactPhone}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Billing Email</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{customer.billingEmail}</div>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-500">Notes</div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{customer.notes}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Recent Loads</h2>
              <div className="space-y-3">
                {customer.recentLoads.map((load) => (
                  <Link
                    key={load.id}
                    href={`/dashboard/loads/${load.id}`}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                  >
                    <div>
                      <div className="text-sm font-medium text-slate-900">{load.loadNumber}</div>
                      <div className="text-xs text-slate-500">{load.id}</div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-slate-700">{load.amount}</span>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          load.status === "needs_review"
                            ? "bg-amber-100 text-amber-800"
                            : load.status === "validated"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {load.status.replace("_", " ")}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Onboarding Readiness</h2>
              <div className="space-y-3">
                {readinessItems.map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-slate-800">{label}</div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        value
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {value ? "Yes" : "No"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Quick Actions</h2>
              <div className="space-y-3">
                <Link
                  href="/dashboard/onboarding"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Open Onboarding
                </Link>
                <Link
                  href="/dashboard/billing"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Open Billing
                </Link>
                <Link
                  href="/dashboard/support"
                  className="block rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Open Support
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}