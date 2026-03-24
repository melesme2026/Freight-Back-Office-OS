"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type Driver = {
  id: string;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
};

export function useDrivers() {
  const [data, setData] = useState<Driver[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchDrivers() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: Driver[] }>("/drivers", {
        token: token ?? undefined,
      });

      setData(response.data ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch drivers";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchDrivers();
  }, []);

  return {
    drivers: data,
    isLoading,
    error,
    refetch: fetchDrivers,
  };
}