"use client";

import { useCallback, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type ReviewQueueItem = {
  load_id: string;
  load_number?: string;
  issue_count: number;
  primary_issue?: string;
  severity?: string;
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

function asNonNegativeInteger(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return Math.floor(value);
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.length === 0) {
      return 0;
    }

    const parsed = Number(trimmed);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return Math.floor(parsed);
    }
  }

  return 0;
}

function normalizeReviewQueueItem(item: unknown): ReviewQueueItem | null {
  const record = asRecord(item);

  if (!record) {
    return null;
  }

  const loadId = asString(record.load_id) ?? asString(record.loadId) ?? asString(record.id);
  if (!loadId) {
    return null;
  }

  return {
    load_id: loadId,
    load_number:
      asString(record.load_number) ??
      asString(record.loadNumber) ??
      undefined,
    issue_count:
      asNonNegativeInteger(record.issue_count) ||
      asNonNegativeInteger(record.issueCount),
    primary_issue:
      asString(record.primary_issue) ??
      asString(record.primaryIssue) ??
      undefined,
    severity: asString(record.severity) ?? undefined,
  };
}

function normalizeReviewQueueResponse(payload: unknown): ReviewQueueItem[] {
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
    } else if (Array.isArray(root.review_queue)) {
      candidates.push(...root.review_queue);
    } else if (Array.isArray(root.items)) {
      candidates.push(...root.items);
    }
  }

  return candidates
    .map((item) => normalizeReviewQueueItem(item))
    .filter((item): item is ReviewQueueItem => item !== null);
}

export function useReviewQueue() {
  const [data, setData] = useState<ReviewQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReviewQueue = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<unknown>("/review-queue", {
        token: token ?? undefined,
      });

      setData(normalizeReviewQueueResponse(response));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch review queue";
      setError(message);
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchReviewQueue();
  }, [fetchReviewQueue]);

  return {
    reviewQueue: data,
    isLoading,
    error,
    refetch: fetchReviewQueue,
  };
}