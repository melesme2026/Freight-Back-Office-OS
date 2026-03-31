"use client";

import { useCallback, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type BillingSummary = {
  active_subscriptions?: number;
  open_invoices?: number;
  past_due_invoices?: number;
  collected_this_month?: number;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asOptionalNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed.length === 0) {
      return undefined;
    }

    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return undefined;
}

function normalizeBillingSummary(payload: unknown): BillingSummary | null {
  const root = asRecord(payload);

  if (!root) {
    return null;
  }

  const nested = asRecord(root.data);
  const source = nested ?? root;

  return {
    active_subscriptions: asOptionalNumber(source.active_subscriptions),
    open_invoices: asOptionalNumber(source.open_invoices),
    past_due_invoices: asOptionalNumber(source.past_due_invoices),
    collected_this_month: asOptionalNumber(source.collected_this_month),
  };
}

export function useBilling() {
  const [data, setData] = useState<BillingSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBilling = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const token = getAccessToken();

      const response = await apiClient.get<unknown>("/billing-dashboard", {
        token: token ?? undefined,
      });

      const normalized = normalizeBillingSummary(response);
      setData(normalized);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch billing summary";
      setError(message);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const token = getAccessToken();

        const response = await apiClient.get<unknown>("/billing-dashboard", {
          token: token ?? undefined,
        });

        if (!isMounted) {
          return;
        }

        const normalized = normalizeBillingSummary(response);
        setData(normalized);
      } catch (err: unknown) {
        if (!isMounted) {
          return;
        }

        const message =
          err instanceof Error ? err.message : "Failed to fetch billing summary";
        setError(message);
        setData(null);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, []);

  return {
    billing: data,
    isLoading,
    error,
    refetch: fetchBilling,
  };
}