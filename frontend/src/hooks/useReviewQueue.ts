"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

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

function normalizeSeverity(value: unknown): string | undefined {
  const normalized = asString(value)?.toLowerCase();
  return normalized ?? undefined;
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
    severity: normalizeSeverity(record.severity),
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
    .filter((item): item is ReviewQueueItem => item !== null)
    .sort((a, b) => {
      const severityRank = (value?: string) => {
        switch ((value ?? "").toLowerCase()) {
          case "high":
            return 0;
          case "medium":
            return 1;
          case "low":
            return 2;
          default:
            return 3;
        }
      };

      const severityDifference = severityRank(a.severity) - severityRank(b.severity);
      if (severityDifference !== 0) {
        return severityDifference;
      }

      if (b.issue_count !== a.issue_count) {
        return b.issue_count - a.issue_count;
      }

      return (a.load_number ?? a.load_id).localeCompare(b.load_number ?? b.load_id);
    });
}

export function useReviewQueue() {
  const [data, setData] = useState<ReviewQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const fetchReviewQueue = useCallback(async (): Promise<void> => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!organizationId) {
      setError("Missing organization context.");
      setData([]);
      setIsLoading(false);
      return;
    }

    try {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      const response = await apiClient.get<unknown>("/review-queue", {
        token: token ?? undefined,
        organizationId,
        signal: controller.signal,
      });

      if (!isMountedRef.current) {
        return;
      }

      setData(normalizeReviewQueueResponse(response));
    } catch (err: unknown) {
      if ((err as { name?: string })?.name === "AbortError") {
        return;
      }

      const message =
        err instanceof Error ? err.message : "Failed to fetch review queue";

      if (isMountedRef.current) {
        setError(message);
        setData([]);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    void fetchReviewQueue();

    return () => {
      isMountedRef.current = false;
      abortRef.current?.abort();
    };
  }, [fetchReviewQueue]);

  return {
    reviewQueue: data,
    isLoading,
    error,
    refetch: fetchReviewQueue,
  };
}