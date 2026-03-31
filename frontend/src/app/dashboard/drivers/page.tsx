"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type DriverListItem = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  status: string;
  loads: number | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asNullableString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function asNullableNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.length === 0) {
      return null;
    }

    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function statusBadgeClass(status?: string): string {
  switch ((status ?? "").toLowerCase()) {
    case "active":
      return "bg-emerald-100 text-emerald-800";
    case "inactive":
      return "bg-slate-200 text-slate-700";
    case "suspended":
      return "bg-rose-100 text-rose-800";
    case "pending":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function statusLabel(status?: string): string {
  const normalized = status?.trim();
  return normalized && normalized.length > 0 ? normalized : "Unknown";
}

function normalizeDriver(record: Record<string, unknown>): DriverListItem | null {
  const id = asNullableString(record.id) ?? asNullableString(record.driver_id);

  if (!id) {
    return null;
  }

  const firstName =
    asNullableString(record.first_name) ?? asNullableString(record.firstName);
  const lastName =
    asNullableString(record.last_name) ?? asNullableString(record.lastName);

  const combinedName = [firstName, lastName]
    .filter((part): part is string => Boolean(part))
    .join(" ")
    .trim();

  const resolvedName =
    asNullableString(record.name) ??
    (combinedName.length > 0 ? combinedName : null) ??
    "Unknown driver";

  return {
    id,
    name: resolvedName,
    phone:
      asNullableString(record.phone) ?? asNullableString(record.phone_number),
    email: asNullableString(record.email),
    status:
      asNullableString(record.status) ??
      asNullableString(record.driver_status) ??
      "unknown",
    loads:
      asNullableNumber(record.loads) ??
      asNullableNumber(record.load_count) ??
      asNullableNumber(record.active_load_count),
  };
}

function normalizeDriversResponse(payload: unknown): DriverListItem[] {
  const candidates: unknown[] = [];

  if (Array.isArray(payload)) {
    candidates.push(...payload);
  } else {
    const root = asRecord(payload);

    if (!root) {
      return [];
    }

    if (Array.isArray(root.data)) {
      candidates.push(...root.data);
    }

    if (Array.isArray(root.drivers)) {
      candidates.push(...root.drivers);
    }

    if (Array.isArray(root.items)) {
      candidates.push(...root.items);
    }
  }

  return candidates
    .map((item) => {
      const record = asRecord(item);
      return record ? normalizeDriver(record) : null;
    })
    .filter((item): item is DriverListItem => item !== null);
}

export default function DriversPage() {
  const router = useRouter();

  const [drivers, setDrivers] = useState<DriverListItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;

    async function loadDrivers() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/v1/drivers", {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
          cache: "no-store",
        });

        if (!response.ok) {
          let message = `Failed to load drivers (${response.status})`;

          try {
            const errorPayload = (await response.json()) as unknown;
            const errorRecord = asRecord(errorPayload);
            const detail =
              asNullableString(errorRecord?.detail) ??
              asNullableString(errorRecord?.message);

            if (detail) {
              message = detail;
            }
          } catch {
            // Keep default message when error payload is not JSON.
          }

          throw new Error(message);
        }

        const payload = (await response.json()) as unknown;
        const normalized = normalizeDriversResponse(payload);

        if (isMounted) {
          setDrivers(normalized);
        }
      } catch (caught) {
        if (isMounted) {
          const message =
            caught instanceof Error
              ? caught.message
              : "An unexpected error occurred while loading drivers.";

          setError(message);
          setDrivers([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadDrivers();

    return () => {
      isMounted = false;
    };
  }, [reloadKey]);

  const driverStats = useMemo(() => {
    const totalDrivers = drivers.length;
    const activeDrivers = drivers.filter(
      (driver) => driver.status.toLowerCase() === "active"
    ).length;
    const inactiveDrivers = drivers.filter(
      (driver) => driver.status.toLowerCase() === "inactive"
    ).length;

    const totalLoads = drivers.reduce((sum, driver) => {
      return sum + (driver.loads ?? 0);
    }, 0);

    return {
      totalDrivers,
      activeDrivers,
      inactiveDrivers,
      totalLoads,
    };
  }, [drivers]);

  const openDriver = (driverId: string) => {
    router.push(`/dashboard/drivers/${driverId}`);
  };

  const refreshDrivers = () => {
    router.refresh();
    setReloadKey((current) => current + 1);
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
              onClick={refreshDrivers}
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

        <section className="grid gap-4 md:grid-cols-4">
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

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Linked loads</div>
            <div className="mt-2 text-3xl font-bold text-brand-700">
              {isLoading ? "..." : driverStats.totalLoads}
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
                onClick={refreshDrivers}
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
                  <th className="px-5 py-4 font-semibold">Loads</th>
                  <th className="px-5 py-4 font-semibold">Action</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-10 text-center text-slate-500"
                    >
                      Loading drivers...
                    </td>
                  </tr>
                ) : drivers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
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
                          {driver.name}
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
                            driver.status
                          )}`}
                        >
                          {statusLabel(driver.status)}
                        </span>
                      </td>

                      <td className="px-5 py-4 font-medium text-slate-900">
                        {driver.loads ?? "—"}
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