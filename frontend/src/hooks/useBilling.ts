"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type BillingSummary = {
  active_subscriptions?: number;
  open_invoices?: number;
  past_due_invoices?: number;
  collected_this_month?: number;
};

export function useBilling() {
  const [data, setData] = useState<BillingSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchBilling() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: BillingSummary }>(
        "/billing-dashboard",
        {
          token: token ?? undefined,
        }
      );

      setData(response.data ?? null);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch billing summary";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchBilling();
  }, []);

  return {
    billing: data,
    isLoading,
    error,
    refetch: fetchBilling,
  };
}