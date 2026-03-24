"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type ReviewQueueItem = {
  load_id: string;
  load_number?: string;
  issue_count: number;
  primary_issue?: string;
  severity?: string;
};

export function useReviewQueue() {
  const [data, setData] = useState<ReviewQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchReviewQueue() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: ReviewQueueItem[] }>(
        "/review-queue",
        {
          token: token ?? undefined,
        }
      );

      setData(response.data ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch review queue";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchReviewQueue();
  }, []);

  return {
    reviewQueue: data,
    isLoading,
    error,
    refetch: fetchReviewQueue,
  };
}