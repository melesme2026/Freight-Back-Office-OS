"use client";

import { useCallback, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type NotificationItem = {
  id: string;
  channel: string;
  direction: string;
  status: string;
  subject?: string | null;
  created_at?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function normalizeNotification(item: unknown): NotificationItem | null {
  const record = asRecord(item);

  if (!record) {
    return null;
  }

  const id = asString(record.id) ?? asString(record.notification_id);
  if (!id) {
    return null;
  }

  return {
    id,
    channel: asString(record.channel) ?? "unknown",
    direction: asString(record.direction) ?? "unknown",
    status: asString(record.status) ?? "unknown",
    subject: asString(record.subject),
    created_at:
      asString(record.created_at) ?? asString(record.createdAt) ?? null,
  };
}

function normalizeNotificationsResponse(payload: unknown): NotificationItem[] {
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
    } else if (Array.isArray(root.notifications)) {
      candidates.push(...root.notifications);
    } else if (Array.isArray(root.items)) {
      candidates.push(...root.items);
    }
  }

  return candidates
    .map((item) => normalizeNotification(item))
    .filter((item): item is NotificationItem => item !== null);
}

export function useNotifications() {
  const [data, setData] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<unknown>("/notifications", {
        token: token ?? undefined,
      });

      setData(normalizeNotificationsResponse(response));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch notifications";
      setError(message);
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchNotifications();
  }, [fetchNotifications]);

  return {
    notifications: data,
    isLoading,
    error,
    refetch: fetchNotifications,
  };
}