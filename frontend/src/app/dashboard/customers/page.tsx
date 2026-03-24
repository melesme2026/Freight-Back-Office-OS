import Link from "next/link";

const customers = [
  {
    id: "cust-1001",
    accountName: "Demo Customer Account",
    accountCode: "DEMO-001",
    status: "active",
    primaryContact: "Demo Dispatcher",
    billingEmail: "billing@demo-freight.com",
    openLoads: 6,
  },
  {
    id: "cust-1002",
    accountName: "North Route Logistics",
    accountCode: "NRL-002",
    status: "active",
    primaryContact: "Sara Kidane",
    billingEmail: "billing@northroutelogistics.com",
    openLoads: 3,
  },
  {
    id: "cust-1003",
    accountName: "Metro Freight Group",
    accountCode: "MFG-003",
    status: "prospect",
    primaryContact: "Michael Alem",
    billingEmail: "finance@metrofreightgroup.com",
    openLoads: 0,
  },
];

function badgeClass(status: string) {
  switch (status) {
    case "active":
      return "bg-emerald-100 text-emerald-800";
    case "prospect":
      return "bg-amber-100 text-amber-800";
    case "inactive":
      return "bg-slate-200 text-slate-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export default function CustomersPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Customers</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Customer Accounts</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage freight customers, operational readiness, billing contacts, and account-level
              activity.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            New Customer Account
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Account</th>
                  <th className="px-5 py-4 font-semibold">Code</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Primary Contact</th>
                  <th className="px-5 py-4 font-semibold">Billing Email</th>
                  <th className="px-5 py-4 font-semibold">Open Loads</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {customers.map((customer) => (
                  <tr key={customer.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{customer.accountName}</div>
                      <div className="text-xs text-slate-500">{customer.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{customer.accountCode}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badgeClass(customer.status)}`}
                      >
                        {customer.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{customer.primaryContact}</td>
                    <td className="px-5 py-4 text-slate-700">{customer.billingEmail}</td>
                    <td className="px-5 py-4 font-medium text-slate-900">{customer.openLoads}</td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/dashboard/customers/${customer.id}`}
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