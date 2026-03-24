"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type Load = {
  id: string;
  load_number: string;
  status: string;
  total_amount?: number;
};

export function useLoads() {
  const [data, setData] = useState<Load[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchLoads() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: Load[] }>("/loads", {
        token: token ?? undefined,
      });

      setData(response.data ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch loads";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchLoads();
  }, []);

  return {
    loads: data,
    isLoading,
    error,
    refetch: fetchLoads,
  };
}