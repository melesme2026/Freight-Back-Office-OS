"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type DriverDetailView = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  status: string;
  customerName: string | null;
  notes: string | null;
  createdAt: string | null;
  updatedAt: string | null;
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

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
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
  return normalized && normalized.length > 0 ? normalized : "unknown";
}

function normalizeDriverDetail(
  payload: unknown,
  driverId: string
): DriverDetailView | null {
  const root = asRecord(payload);
  if (!root) {
    return null;
  }

  const container =
    asRecord(root.data) ??
    asRecord(root.driver) ??
    asRecord(root.item) ??
    root;

  const firstName =
    asNullableString(container.first_name) ??
    asNullableString(container.firstName);
  const lastName =
    asNullableString(container.last_name) ??
    asNullableString(container.lastName);

  const combinedName = [firstName, lastName].filter(Boolean).join(" ").trim();
  const fallbackName = combinedName.length > 0 ? combinedName : null;

  const resolvedName =
    asNullableString(container.name) ??
    fallbackName ??
    "Unknown driver";

  return {
    id:
      asNullableString(container.id) ??
      asNullableString(container.driver_id) ??
      driverId,
    name: resolvedName,
    phone:
      asNullableString(container.phone) ??
      asNullableString(container.phone_number),
    email: asNullableString(container.email),
    status:
      asNullableString(container.status) ??
      asNullableString(container.driver_status) ??
      "unknown",
    customerName:
      asNullableString(container.customer_name) ??
      asNullableString(container.customer) ??
      asNullableString(container.account_name),
    notes:
      asNullableString(container.notes) ??
      asNullableString(container.operational_notes),
    createdAt:
      asNullableString(container.created_at) ??
      asNullableString(container.createdAt),
    updatedAt:
      asNullableString(container.updated_at) ??
      asNullableString(container.updatedAt),
  };
}

export default function DriverDetailPage() {
  const router = useRouter();
  const params = useParams();

  const rawDriverId = params?.driverId;
  const driverId = Array.isArray(rawDriverId)
    ? rawDriverId[0] ?? ""
    : typeof rawDriverId === "string"
      ? rawDriverId
      : "";

  const [driver, setDriver] = useState<DriverDetailView | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDriver() {
      if (!driverId) {
        if (isMounted) {
          setError("Driver ID is missing.");
          setDriver(null);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/v1/drivers/${encodeURIComponent(driverId)}`,
          {
            method: "GET",
            credentials: "include",
            headers: {
              Accept: "application/json",
            },
            cache: "no-store",
          }
        );

        if (!response.ok) {
          let message = `Failed to load driver (${response.status})`;

          try {
            const errorPayload = (await response.json()) as unknown;
            const errorRecord = asRecord(errorPayload);
            const errorNode = asRecord(errorRecord?.error);
            const detail =
              asNullableString(errorRecord?.detail) ??
              asNullableString(errorRecord?.message) ??
              asNullableString(errorNode?.message);

            if (detail) {
              message = detail;
            }
          } catch {
            // Keep default message when payload is not JSON.
          }

          throw new Error(message);
        }

        const payload = (await response.json()) as unknown;
        const normalized = normalizeDriverDetail(payload, driverId);

        if (!normalized) {
          throw new Error("Driver response could not be normalized.");
        }

        if (isMounted) {
          setDriver(normalized);
        }
      } catch (caught) {
        if (isMounted) {
          const message =
            caught instanceof Error
              ? caught.message
              : "An unexpected error occurred while loading the driver.";

          setError(message);
          setDriver(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadDriver();

    return () => {
      isMounted = false;
    };
  }, [driverId]);

  const quickStats = useMemo(
    () => [
      {
        label: "Phone",
        value: driver?.phone ?? "—",
      },
      {
        label: "Email",
        value: driver?.email ?? "—",
      },
      {
        label: "Customer",
        value: driver?.customerName ?? "—",
      },
      {
        label: "Driver ID",
        value: driver?.id ?? (driverId || "—"),
      },
      {
        label: "Created",
        value: formatDateTime(driver?.createdAt ?? null),
      },
      {
        label: "Updated",
        value: formatDateTime(driver?.updatedAt ?? null),
      },
    ],
    [driver, driverId]
  );

  const handleBack = () => {
    router.back();
  };

  const openDrivers = () => {
    router.push("/dashboard/drivers");
  };

  const openLoads = () => {
    router.push("/dashboard/loads");
  };

  const openSupport = () => {
    router.push("/dashboard/support");
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Loading driver...
            </h1>
            <p className="mt-3 text-sm text-slate-600">
              Fetching driver profile and operational details.
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-rose-800">
              Unable to load driver
            </h1>
            <p className="mt-2 text-sm text-rose-700">{error}</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={openDrivers}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Open Drivers
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!driver) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers / Detail
            </p>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">
              Driver not found
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              No driver matched ID:
            </p>
            <p className="mt-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-800">
              {driverId || "—"}
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleBack}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Go Back
              </button>
              <button
                type="button"
                onClick={openDrivers}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Open Drivers
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8">
          <button
            type="button"
            onClick={handleBack}
            className="text-sm font-medium text-brand-700 hover:text-brand-800"
          >
            ← Back
          </button>
        </div>

        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Drivers / Detail
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              {driver.name}
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Driver profile, contact details, account context, and operational
              readiness for V1.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Driver editing is not yet wired in V1."
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 opacity-60"
            >
              Edit Driver
            </button>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Driver-specific load creation is not yet wired in V1."
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
            >
              New Load
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr,1fr]">
          <section className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">
                  Driver Summary
                </h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(
                    driver.status
                  )}`}
                >
                  {statusLabel(driver.status)}
                </span>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {quickStats.map((item) => (
                  <div key={item.label}>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      {item.label}
                    </div>
                    <div className="mt-1 break-words text-sm font-medium text-slate-900">
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Operational Notes
              </h2>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm leading-6 text-slate-700">
                  {driver.notes?.trim()
                    ? driver.notes
                    : "No operational notes have been added for this driver yet."}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="mb-4 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-950">
                  Operational Follow-Up
                </h2>
                <button
                  type="button"
                  onClick={openLoads}
                  className="text-sm font-semibold text-brand-700 hover:text-brand-800"
                >
                  Open Loads →
                </button>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-700">
                  Driver-specific recent load history is not yet wired from a
                  dedicated backend relation endpoint. For V1, use the Loads
                  workspace to review current freight activity.
                </p>
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">
                Quick Actions
              </h2>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={openDrivers}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Back to Drivers
                </button>
                <button
                  type="button"
                  onClick={openLoads}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  View All Loads
                </button>
                <button
                  type="button"
                  onClick={openSupport}
                  className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Open Support
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}