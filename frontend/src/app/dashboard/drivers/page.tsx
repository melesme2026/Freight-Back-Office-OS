"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { useDrivers } from "@/hooks/useDrivers";

function statusBadgeClass(isActive: boolean): string {
  return isActive
    ? "bg-emerald-100 text-emerald-800"
    : "bg-slate-200 text-slate-700";
}

function statusLabel(isActive: boolean): string {
  return isActive ? "Active" : "Inactive";
}

export default function DriversPage() {
  const router = useRouter();
  const { drivers, isLoading, error, refetch } = useDrivers();

  const driverStats = useMemo(() => {
    const totalDrivers = drivers.length;
    const activeDrivers = drivers.filter((driver) => driver.is_active).length;
    const inactiveDrivers = drivers.filter((driver) => !driver.is_active).length;

    return {
      totalDrivers,
      activeDrivers,
      inactiveDrivers,
    };
  }, [drivers]);

  const openDriver = (driverId: string) => {
    router.push(`/dashboard/drivers/${driverId}`);
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Drivers
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Manage drivers, contact information, activity, and related freight
              operations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void refetch()}
              disabled={isLoading}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Driver creation is not yet wired in V1."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              Add Driver
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total drivers</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : driverStats.totalDrivers}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Active</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">
              {isLoading ? "..." : driverStats.activeDrivers}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Inactive</div>
            <div className="mt-2 text-3xl font-bold text-slate-700">
              {isLoading ? "..." : driverStats.inactiveDrivers}
            </div>
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-sm font-semibold text-rose-800">
                  Unable to load drivers
                </h2>
                <p className="mt-1 text-sm text-rose-700">{error}</p>
              </div>

              <button
                type="button"
                onClick={() => void refetch()}
                className="inline-flex items-center rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Driver</th>
                  <th className="px-5 py-4 font-semibold">Phone</th>
                  <th className="px-5 py-4 font-semibold">Email</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-5 py-10 text-center text-slate-500"
                    >
                      Loading drivers...
                    </td>
                  </tr>
                ) : drivers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-5 py-10 text-center text-slate-500"
                    >
                      No drivers found.
                    </td>
                  </tr>
                ) : (
                  drivers.map((driver) => (
                    <tr key={driver.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900">
                          {driver.full_name}
                        </div>
                        <div className="text-xs text-slate-500">{driver.id}</div>
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {driver.phone ?? "—"}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {driver.email ?? "—"}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(
                            driver.is_active
                          )}`}
                        >
                          {statusLabel(driver.is_active)}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={() => openDriver(driver.id)}
                          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}