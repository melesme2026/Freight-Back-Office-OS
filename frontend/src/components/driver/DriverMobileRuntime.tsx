"use client";

import { useEffect, useMemo, useState } from "react";

import { getOrganizationId } from "@/lib/auth";
import {
  getDriverUploadQueue,
  processDriverUploadQueue,
  removeQueuedDriverUpload,
  subscribeToDriverUploadQueue,
  type QueuedDriverUpload,
} from "@/lib/driver-mobile";

const PUSH_PREF_KEY = "adwa.driver.pushPreferences.v1";

type PushPreferences = {
  missingPodReminder: boolean;
  uploadBlockedReminder: boolean;
  dispatcherRequest: boolean;
};

const DEFAULT_PUSH_PREFS: PushPreferences = {
  missingPodReminder: true,
  uploadBlockedReminder: true,
  dispatcherRequest: true,
};

function loadPushPreferences(): PushPreferences {
  if (typeof window === "undefined") return DEFAULT_PUSH_PREFS;
  const raw = window.localStorage.getItem(PUSH_PREF_KEY);
  if (!raw) return DEFAULT_PUSH_PREFS;
  try {
    return { ...DEFAULT_PUSH_PREFS, ...(JSON.parse(raw) as Partial<PushPreferences>) };
  } catch {
    return DEFAULT_PUSH_PREFS;
  }
}

function storePushPreferences(preferences: PushPreferences): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PUSH_PREF_KEY, JSON.stringify(preferences));
}

export default function DriverMobileRuntime() {
  const [isOnline, setIsOnline] = useState(true);
  const [queue, setQueue] = useState<QueuedDriverUpload[]>([]);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [pushPreferences, setPushPreferences] = useState<PushPreferences>(DEFAULT_PUSH_PREFS);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | "unsupported">("unsupported");

  const queuedCount = queue.length;
  const failedCount = useMemo(() => queue.filter((item) => item.lastError).length, [queue]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const refresh = () => {
      setIsOnline(window.navigator.onLine);
      setQueue(getDriverUploadQueue());
    };

    refresh();
    setPushPreferences(loadPushPreferences());
    if ("Notification" in window) setNotificationPermission(window.Notification.permission);

    window.addEventListener("online", refresh);
    window.addEventListener("offline", refresh);
    const unsubscribeQueue = subscribeToDriverUploadQueue(refresh);

    return () => {
      window.removeEventListener("online", refresh);
      window.removeEventListener("offline", refresh);
      unsubscribeQueue();
    };
  }, []);

  useEffect(() => {
    if (!isOnline || queuedCount === 0) return;
    void syncQueuedUploads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline, queuedCount]);

  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  }, []);

  async function syncQueuedUploads() {
    const organizationId = getOrganizationId();
    if (!organizationId) return;

    setSyncMessage("Syncing queued documents…");
    const result = await processDriverUploadQueue({
      organizationId,
      onSynced: (item) => setSyncMessage(`Synced ${item.fileName}. Dispatch can now review it.`),
    });
    setQueue(getDriverUploadQueue());
    if (result.synced > 0) {
      setSyncMessage(result.remaining > 0 ? `${result.synced} queued document synced. ${result.remaining} still queued for retry.` : `${result.synced} queued document synced. Dispatch can now review it.`);
    } else if (result.remaining > 0) {
      setSyncMessage("Queued documents will retry automatically when the connection is stable.");
    } else {
      setSyncMessage(null);
    }
  }

  async function enableNotifications() {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setNotificationPermission("unsupported");
      return;
    }
    const permission = await window.Notification.requestPermission();
    setNotificationPermission(permission);
  }

  function updatePreference(key: keyof PushPreferences, value: boolean) {
    const next = { ...pushPreferences, [key]: value };
    setPushPreferences(next);
    storePushPreferences(next);
  }

  return (
    <aside className="mx-auto max-w-6xl px-4 pt-4 sm:px-6" aria-label="Driver mobile sync status">
      <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
        <div className={`rounded-2xl border px-4 py-3 text-sm shadow-soft ${isOnline ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold">{isOnline ? "Online and ready to upload" : "Offline mode active"}</p>
              <p className="mt-1 text-xs">{queuedCount > 0 ? `${queuedCount} upload${queuedCount === 1 ? "" : "s"} queued${failedCount ? ` · ${failedCount} need connection attention` : ""}.` : "No pending document uploads."} {syncMessage ?? ""}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => void syncQueuedUploads()} disabled={!isOnline || queuedCount === 0} className="touch-target rounded-xl bg-white px-3 py-2 text-xs font-semibold text-slate-800 ring-1 ring-inset ring-slate-200 disabled:cursor-not-allowed disabled:opacity-60">
                Sync now
              </button>
            </div>
          </div>
          {queuedCount > 0 ? (
            <div className="mt-3 space-y-2">
              {queue.slice(0, 3).map((item) => (
                <div key={item.id} className="flex flex-col gap-2 rounded-xl bg-white/80 px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between">
                  <span className="break-all font-medium">{item.fileName} · {item.documentType.replaceAll("_", " ")}</span>
                  <button type="button" onClick={() => removeQueuedDriverUpload(item.id)} className="touch-target rounded-lg border border-slate-200 px-2 py-1 font-semibold text-slate-700">
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <details className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-soft">
          <summary className="cursor-pointer font-semibold text-slate-900">Push reminders</summary>
          <p className="mt-2 text-xs text-slate-500">Browser permission and driver preferences for future missing POD, blocked upload, and dispatcher request reminders.</p>
          <button type="button" onClick={() => void enableNotifications()} className="touch-target mt-3 rounded-xl bg-brand-600 px-3 py-2 text-xs font-semibold text-white">
            {notificationPermission === "granted" ? "Notifications enabled" : "Enable notifications"}
          </button>
          <div className="mt-3 space-y-2 text-xs">
            {([
              ["missingPodReminder", "Missing POD reminders"],
              ["uploadBlockedReminder", "Blocked upload reminders"],
              ["dispatcherRequest", "Dispatcher requests"],
            ] as const).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2">
                <input type="checkbox" checked={pushPreferences[key]} onChange={(event) => updatePreference(key, event.target.checked)} />
                {label}
              </label>
            ))}
          </div>
        </details>
      </div>
    </aside>
  );
}
