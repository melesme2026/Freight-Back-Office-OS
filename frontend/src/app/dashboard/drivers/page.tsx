import Link from "next/link";

const drivers = [
  {
    id: "driver-1001",
    name: "Demo Driver",
    phone: "+1 (586) 555-0101",
    email: "driver@demo-freight.com",
    status: "active",
    loads: 8,
  },
  {
    id: "driver-1002",
    name: "Sam Haile",
    phone: "+1 (586) 555-0102",
    email: "sam@demo-freight.com",
    status: "active",
    loads: 5,
  },
  {
    id: "driver-1003",
    name: "Daniel Tes",
    phone: "+1 (586) 555-0103",
    email: "daniel@demo-freight.com",
    status: "inactive",
    loads: 1,
  },
];

export default function DriversPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Drivers</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">Drivers</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage drivers, contact information, activity, and their related freight paperwork.
            </p>
          </div>

          <button className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
            Add Driver
          </button>
        </div>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Driver</th>
                  <th className="px-5 py-4 font-semibold">Phone</th>
                  <th className="px-5 py-4 font-semibold">Email</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Loads</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {drivers.map((driver) => (
                  <tr key={driver.id} className="hover:bg-slate-50">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{driver.name}</div>
                      <div className="text-xs text-slate-500">{driver.id}</div>
                    </td>
                    <td className="px-5 py-4 text-slate-700">{driver.phone}</td>
                    <td className="px-5 py-4 text-slate-700">{driver.email}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                          driver.status === "active"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {driver.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-medium text-slate-900">{driver.loads}</td>
                    <td className="px-5 py-4">
                      <Link
                        href={`/dashboard/drivers/${driver.id}`}
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