"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { copyTextWithFallback } from "@/lib/clipboard";

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
    asNullableString(container.full_name) ??
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
      (container.is_active === true ? "active" : container.is_active === false ? "inactive" : "unknown"),
    customerName:
      asNullableString(container.customer_name) ??
      asNullableString(container.customer) ??
      asNullableString(container.account_name) ??
      asNullableString(container.customer_account_name),
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
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [activationUrl, setActivationUrl] = useState<string | null>(null);
  const [inviteStatus, setInviteStatus] = useState<string | null>(null);
  const [inviteEmailStatus, setInviteEmailStatus] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTogglingActive, setIsTogglingActive] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");

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

      const token = getAccessToken();
      const organizationId = getOrganizationId();

      if (!token || !organizationId) {
        if (isMounted) {
          setError("Missing session context. Please sign in again.");
          setDriver(null);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const payload = await apiClient.get<unknown>(
          `/drivers/${encodeURIComponent(driverId)}`,
          {
            token,
            organizationId,
          }
        );

        const normalized = normalizeDriverDetail(payload, driverId);

        if (!normalized) {
          throw new Error("Driver response could not be normalized.");
        }

        if (isMounted) {
          setDriver(normalized);
          setEditFullName(normalized.name);
          setEditPhone(normalized.phone ?? "");
          setEditEmail(normalized.email ?? "");
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

  async function inviteDriverToPortal() {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setInviteError("Missing session context. Please sign in again.");
      return;
    }

    if (!driver?.email) {
      setInviteError("Driver email is required before generating an invite. Add and save an email first.");
      return;
    }

    try {
      setIsInviting(true);
      setInviteError(null);
      setActivationUrl(null);
      setInviteStatus(null);
      setInviteEmailStatus(null);

      const payload = await apiClient.post<{
        data?: { activation_token?: string; activation_url?: string; email_status?: string };
      }>(
        "/auth/invite-user",
        {
          email: driver.email,
          full_name: driver.name,
          role: "driver",
          organization_id: organizationId,
        },
        {
          token,
          organizationId,
        }
      );

      const activationUrlValue = payload?.data?.activation_url?.trim() || null;
      const emailStatus = payload?.data?.email_status?.trim() || "sent";
      const tokenValue = payload?.data?.activation_token?.trim();
      const resolvedActivationUrl = activationUrlValue || (tokenValue ? `/activate-account?token=${encodeURIComponent(tokenValue)}` : null);

      setInviteEmailStatus(emailStatus);
      setInviteStatus(
        emailStatus === "disabled"
          ? "Activation link ready."
          : `Invite sent to ${driver.email}.`
      );
      setActivationUrl(resolvedActivationUrl);
    } catch (caught: unknown) {
      setInviteError(
        caught instanceof Error
          ? `${caught.message} (Confirm this email matches an existing driver profile before inviting.)`
          : "Unable to generate driver invite. Confirm driver profile email is saved first."
      );
    } finally {
      setIsInviting(false);
    }
  }

  async function copyActivationLink() {
    const relativeLink = activationUrl;
    if (!relativeLink) {
      return;
    }

    const absoluteLink = relativeLink.startsWith("http") ? relativeLink : `${window.location.origin}${relativeLink}`;
    const copied = await copyTextWithFallback(absoluteLink);
    if (copied) {
      setInviteStatus("Activation link copied.");
      return;
    }
    setInviteStatus("Copy failed — select and copy the link manually.");
  }

  async function saveDriverEdits() {
    if (!driver) {
      return;
    }

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setUpdateError("Missing session context. Please sign in again.");
      return;
    }

    if (!editFullName.trim()) {
      setUpdateError("Driver name is required.");
      return;
    }

    if (!editPhone.trim()) {
      setUpdateError("Driver phone is required.");
      return;
    }

    try {
      setIsSaving(true);
      setUpdateError(null);
      setUpdateMessage(null);

      const payload = await apiClient.patch<unknown>(
        `/drivers/${encodeURIComponent(driver.id)}`,
        {
          full_name: editFullName.trim(),
          phone: editPhone.trim(),
          email: editEmail.trim() ? editEmail.trim() : null,
        },
        {
          token,
          organizationId,
        }
      );

      const normalized = normalizeDriverDetail(payload, driver.id);
      if (!normalized) {
        throw new Error("Updated driver response could not be normalized.");
      }

      setDriver(normalized);
      setEditFullName(normalized.name);
      setEditPhone(normalized.phone ?? "");
      setEditEmail(normalized.email ?? "");
      setIsEditing(false);
      setUpdateMessage("Driver profile updated.");
    } catch (caught: unknown) {
      setUpdateError(caught instanceof Error ? caught.message : "Unable to update driver.");
    } finally {
      setIsSaving(false);
    }
  }

  async function toggleDriverActiveState() {
    if (!driver) {
      return;
    }

    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setUpdateError("Missing session context. Please sign in again.");
      return;
    }

    try {
      setIsTogglingActive(true);
      setUpdateError(null);
      setUpdateMessage(null);

      const nextIsActive = driver.status.toLowerCase() !== "active";
      const payload = nextIsActive
        ? await apiClient.patch<unknown>(
            `/drivers/${encodeURIComponent(driver.id)}/reactivate`,
            undefined,
            {
              token,
              organizationId,
            }
          )
        : await apiClient.patch<unknown>(
            `/drivers/${encodeURIComponent(driver.id)}`,
            {
              is_active: false,
            },
            {
              token,
              organizationId,
            }
          );

      const normalized = normalizeDriverDetail(payload, driver.id);
      if (!normalized) {
        throw new Error("Updated driver response could not be normalized.");
      }

      setDriver(normalized);
      setUpdateMessage(nextIsActive ? "Driver reactivated." : "Driver deactivated.");
    } catch (caught: unknown) {
      setUpdateError(caught instanceof Error ? caught.message : "Unable to update driver status.");
    } finally {
      setIsTogglingActive(false);
    }
  }

  if (isLoading) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  if (!driver) {
    return (
      <div className="px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-7xl">
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
      </div>
    );
  }

  return (
    <div className="px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-7xl">
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
              readiness for operations.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setIsEditing((current) => !current);
                setUpdateError(null);
                setUpdateMessage(null);
                if (driver) {
                  setEditFullName(driver.name);
                  setEditPhone(driver.phone ?? "");
                  setEditEmail(driver.email ?? "");
                }
              }}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              {isEditing ? "Cancel Edit" : "Edit Driver"}
            </button>
            <button
              type="button"
              onClick={() => void toggleDriverActiveState()}
              disabled={isTogglingActive}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-60"
            >
              {isTogglingActive
                ? "Saving..."
                : driver.status.toLowerCase() === "active"
                  ? "Deactivate Driver"
                  : "Reactivate Driver"}
            </button>
            <button
              type="button"
              onClick={openLoads}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              View Loads
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

              {updateError ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {updateError}
                </div>
              ) : null}
              {updateMessage ? (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {updateMessage}
                </div>
              ) : null}

              {isEditing ? (
                <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <input
                      type="text"
                      value={editFullName}
                      onChange={(event) => setEditFullName(event.target.value)}
                      placeholder="Driver full name"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                    <input
                      type="text"
                      value={editPhone}
                      onChange={(event) => setEditPhone(event.target.value)}
                      placeholder="Phone"
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isSaving}
                    />
                  </div>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(event) => setEditEmail(event.target.value)}
                    placeholder="Email (optional)"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
                    disabled={isSaving}
                  />
                  <button
                    type="button"
                    onClick={() => void saveDriverEdits()}
                    disabled={isSaving}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
                  >
                    {isSaving ? "Saving..." : "Save Driver Changes"}
                  </button>
                </div>
              ) : null}
              {driver.status.toLowerCase() !== "active" ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Inactive drivers cannot sign in, but historical loads and documents remain available.
                </div>
              ) : null}
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
                  Review current and recent freight activity from the Loads workspace. Driver-specific activity will appear here as loads are assigned and documents are received.
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-slate-950">Driver Portal Invite</h2>
              <p className="mt-2 text-sm text-slate-600">
                Generate an activation invite for this driver profile. Drivers activate first, then sign in through Driver Login.
              </p>
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                Driver email: <span className="font-semibold">{driver.email ?? "Not set"}</span>
              </div>

              {inviteError ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {inviteError}
                </div>
              ) : null}

              {inviteStatus ? (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  {inviteStatus}
                </div>
              ) : null}

              {inviteEmailStatus === "disabled" ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Email delivery is disabled. Copy the activation link and send it manually.
                </div>
              ) : null}

              {activationUrl ? (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-800">
                  <div className="font-semibold">Activation link generated</div>
                  <input
                    readOnly
                    value={activationUrl.startsWith("http") ? activationUrl : `${typeof window !== "undefined" ? window.location.origin : ""}${activationUrl}`}
                    className="mt-2 w-full rounded-lg border border-emerald-300 bg-white px-3 py-2 text-xs text-slate-800"
                  />
                  <div className="mt-2 flex flex-wrap gap-3">
                    <button type="button" onClick={() => void copyActivationLink()} className="font-semibold text-brand-700">
                      Copy activation link
                    </button>
                    <a href={activationUrl} className="font-semibold text-brand-700">
                      Open activation page
                    </a>
                  </div>
                </div>
              ) : null}

              <button
                type="button"
                onClick={() => void inviteDriverToPortal()}
                disabled={isInviting || !driver.email}
                className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                {isInviting ? "Generating invite..." : "Generate driver activation invite"}
              </button>
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
    </div>
  );
}
