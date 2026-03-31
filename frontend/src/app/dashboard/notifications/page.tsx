"use client";

import { useEffect, useMemo, useState } from "react";

type NotificationItem = {
  id: string;
  channel: string;
  direction: string;
  messageType: string;
  recipient: string;
  status: string;
  subject: string;
  createdAt: string | null;
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

function asString(value: unknown, fallback: string): string {
  const resolved = asNullableString(value);
  return resolved ?? fallback;
}

function normalizeNotification(
  record: Record<string, unknown>
): NotificationItem | null {
  const id =
    asNullableString(record.id) ??
    asNullableString(record.notification_id);

  if (!id) {
    return null;
  }

  return {
    id,
    channel:
      asString(record.channel, "unknown"),
    direction:
      asString(record.direction, "unknown"),
    messageType:
      asString(
        record.message_type ?? record.messageType,
        "unknown"
      ),
    recipient:
      asString(record.recipient, "—"),
    status:
      asString(record.status, "unknown"),
    subject:
      asString(record.subject, "Untitled notification"),
    createdAt:
      asNullableString(record.created_at) ??
      asNullableString(record.createdAt),
  };
}

function normalizeNotificationsResponse(payload: unknown): NotificationItem[] {
  if (Array.isArray(payload)) {
    return payload
      .map((item) => {
        const record = asRecord(item);
        return record ? normalizeNotification(record) : null;
      })
      .filter((item): item is NotificationItem => item !== null);
  }

  const root = asRecord(payload);
  if (!root) {
    return [];
  }

  const candidates =
    Array.isArray(root.data) ? root.data :
    Array.isArray(root.notifications) ? root.notifications :
    Array.isArray(root.items) ? root.items :
    [];

  return candidates
    .map((item) => {
      const record = asRecord(item);
      return record ? normalizeNotification(record) : null;
    })
    .filter((item): item is NotificationItem => item !== null);
}

function statusBadge(status?: string): string {
  switch ((status ?? "").toLowerCase()) {
    case "sent":
      return "bg-emerald-100 text-emerald-800";
    case "queued":
      return "bg-amber-100 text-amber-800";
    case "delivered":
      return "bg-blue-100 text-blue-800";
    case "failed":
      return "bg-rose-100 text-rose-800";
    case "processing":
      return "bg-indigo-100 text-indigo-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function labelize(value?: string | null): string {
  const normalized = value?.trim();
  if (!normalized) {
    return "Unknown";
  }

  return normalized.replaceAll("_", " ");
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

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadNotifications() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/v1/notifications", {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
          cache: "no-store",
        });

        if (!response.ok) {
          let message = `Failed to load notifications (${response.status})`;

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
            // Keep default message when payload is not JSON.
          }

          throw new Error(message);
        }

        const payload = (await response.json()) as unknown;
        const normalized = normalizeNotificationsResponse(payload);

        if (isMounted) {
          setNotifications(normalized);
        }
      } catch (caught) {
        if (isMounted) {
          const message =
            caught instanceof Error
              ? caught.message
              : "An unexpected error occurred while loading notifications.";

          setError(message);
          setNotifications([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadNotifications();

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(() => {
    const totalToday = notifications.length;
    const queued = notifications.filter(
      (item) => item.status.toLowerCase() === "queued"
    ).length;
    const sent = notifications.filter(
      (item) => item.status.toLowerCase() === "sent"
    ).length;
    const failed = notifications.filter(
      (item) => item.status.toLowerCase() === "failed"
    ).length;

    return {
      totalToday,
      queued,
      sent,
      failed,
    };
  }, [notifications]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">
              Dashboard / Notifications
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Notifications
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Track outbound and inbound operational notifications across
              WhatsApp, email, and in-app channels.
            </p>
          </div>

          <button
            type="button"
            disabled
            aria-disabled="true"
            title="Notification creation is not yet wired in V1."
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white opacity-60"
          >
            New Notification
          </button>
        </div>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Total</div>
            <div className="mt-2 text-3xl font-bold text-slate-950">
              {isLoading ? "..." : summary.totalToday}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Queued</div>
            <div className="mt-2 text-3xl font-bold text-amber-600">
              {isLoading ? "..." : summary.queued}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Sent</div>
            <div className="mt-2 text-3xl font-bold text-emerald-700">
              {isLoading ? "..." : summary.sent}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="text-sm text-slate-500">Failed</div>
            <div className="mt-2 text-3xl font-bold text-rose-700">
              {isLoading ? "..." : summary.failed}
            </div>
          </div>
        </section>

        {error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr className="text-left text-slate-600">
                  <th className="px-5 py-4 font-semibold">Notification</th>
                  <th className="px-5 py-4 font-semibold">Channel</th>
                  <th className="px-5 py-4 font-semibold">Direction</th>
                  <th className="px-5 py-4 font-semibold">Recipient</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Created</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-10 text-center text-slate-500"
                    >
                      Loading notifications...
                    </td>
                  </tr>
                ) : notifications.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-10 text-center text-slate-500"
                    >
                      No notifications found.
                    </td>
                  </tr>
                ) : (
                  notifications.map((notification) => (
                    <tr key={notification.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900">
                          {notification.subject}
                        </div>
                        <div className="text-xs text-slate-500">
                          {notification.id}
                        </div>
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {labelize(notification.channel)}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {labelize(notification.direction)}
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {notification.recipient}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusBadge(
                            notification.status
                          )}`}
                        >
                          {labelize(notification.status)}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-slate-700">
                        {formatDateTime(notification.createdAt)}
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