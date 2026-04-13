"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

type CreateNotificationResponse = {
  data?: {
    id?: string;
  };
};

const CHANNEL_OPTIONS = ["web", "whatsapp", "email", "api", "manual"] as const;
const DIRECTION_OPTIONS = ["outbound", "inbound"] as const;

export default function NewNotificationPage() {
  const router = useRouter();
  const [channel, setChannel] = useState<string>("email");
  const [direction, setDirection] = useState<string>("outbound");
  const [messageType, setMessageType] = useState<string>("operational_update");
  const [subject, setSubject] = useState<string>("");
  const [bodyText, setBodyText] = useState<string>("");
  const [customerAccountId, setCustomerAccountId] = useState<string>("");
  const [driverId, setDriverId] = useState<string>("");
  const [loadId, setLoadId] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return messageType.trim().length > 0 && !isSubmitting;
  }, [isSubmitting, messageType]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const organizationId = getOrganizationId();
    const token = getAccessToken();

    if (!organizationId) {
      setErrorMessage("Missing organization context. Please sign in again.");
      return;
    }

    if (!messageType.trim()) {
      setErrorMessage("Message type is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = await apiClient.post<CreateNotificationResponse>(
        "/notifications",
        {
          organization_id: organizationId,
          channel: channel.trim(),
          direction: direction.trim(),
          message_type: messageType.trim(),
          subject: subject.trim() || null,
          body_text: bodyText.trim() || null,
          customer_account_id: customerAccountId.trim() || null,
          driver_id: driverId.trim() || null,
          load_id: loadId.trim() || null,
          status: "queued",
        },
        {
          token: token ?? undefined,
          organizationId,
        }
      );

      const createdId = payload?.data?.id?.trim();
      router.replace(
        createdId
          ? `/dashboard/notifications?created=${encodeURIComponent(createdId)}`
          : "/dashboard/notifications?created=1"
      );
      router.refresh();
    } catch (error: unknown) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Failed to create notification. Please check inputs and try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-brand-700">Dashboard / Notifications</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">New Notification</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Create an operational notification record for outbound or inbound activity.
            </p>
          </div>
          <Link
            href="/dashboard/notifications"
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Back to Notifications
          </Link>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft space-y-5"
          noValidate
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">
              Channel
              <select
                value={channel}
                onChange={(event) => setChannel(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {CHANNEL_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-slate-700">
              Direction
              <select
                value={direction}
                onChange={(event) => setDirection(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {DIRECTION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block text-sm font-medium text-slate-700">
            Message Type
            <input
              type="text"
              value={messageType}
              onChange={(event) => setMessageType(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              placeholder="operational_update"
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Subject
            <input
              type="text"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              placeholder="Optional subject"
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Body
            <textarea
              value={bodyText}
              onChange={(event) => setBodyText(event.target.value)}
              rows={5}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              placeholder="Optional notification body"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-sm font-medium text-slate-700">
              Customer Account ID
              <input
                type="text"
                value={customerAccountId}
                onChange={(event) => setCustomerAccountId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm font-medium text-slate-700">
              Driver ID
              <input
                type="text"
                value={driverId}
                onChange={(event) => setDriverId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm font-medium text-slate-700">
              Load ID
              <input
                type="text"
                value={loadId}
                onChange={(event) => setLoadId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
          </div>

          {errorMessage ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Creating..." : "Create Notification"}
          </button>
        </form>
      </div>
    </main>
  );
}
