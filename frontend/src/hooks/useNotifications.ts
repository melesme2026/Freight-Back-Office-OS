"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type NotificationItem = {
  id: string;
  channel: string;
  direction: string;
  status: string;
  subject?: string | null;
  created_at?: string | null;
};

export function useNotifications() {
  const [data, setData] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchNotifications() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: NotificationItem[] }>(
        "/notifications",
        {
          token: token ?? undefined,
        }
      );

      setData(response.data ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch notifications";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchNotifications();
  }, []);

  return {
    notifications: data,
    isLoading,
    error,
    refetch: fetchNotifications,
  };
}