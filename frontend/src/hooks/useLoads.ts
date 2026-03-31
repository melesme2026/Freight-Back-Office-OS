"use client";

import { useCallback, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type Load = {
  id: string;
  load_number: string;
  status: string;
  gross_amount?: number | string | null;
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

function asGrossAmount(value: unknown): number | string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  return null;
}

function normalizeLoad(item: unknown): Load | null {
  const record = asRecord(item);

  if (!record) {
    return null;
  }

  const id = asString(record.id) ?? asString(record.load_id);
  const loadNumber =
    asString(record.load_number) ??
    asString(record.loadNumber) ??
    asString(record.number);

  if (!id || !loadNumber) {
    return null;
  }

  return {
    id,
    load_number: loadNumber,
    status: asString(record.status) ?? "unknown",
    gross_amount:
      asGrossAmount(record.gross_amount) ??
      asGrossAmount(record.grossAmount) ??
      asGrossAmount(record.amount),
  };
}

function normalizeLoadsResponse(payload: unknown): Load[] {
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
    } else if (Array.isArray(root.loads)) {
      candidates.push(...root.loads);
    } else if (Array.isArray(root.items)) {
      candidates.push(...root.items);
    }
  }

  return candidates
    .map((item) => normalizeLoad(item))
    .filter((item): item is Load => item !== null);
}

export function useLoads() {
  const [data, setData] = useState<Load[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLoads = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<unknown>("/loads", {
        token: token ?? undefined,
      });

      setData(normalizeLoadsResponse(response));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to fetch loads";
      setError(message);
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchLoads();
  }, [fetchLoads]);

  return {
    loads: data,
    isLoading,
    error,
    refetch: fetchLoads,
  };
}