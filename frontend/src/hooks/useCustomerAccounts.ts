"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type CustomerAccount = {
  id: string;
  account_name: string;
  account_code?: string | null;
  status: string;
  billing_email?: string | null;
};

export function useCustomerAccounts() {
  const [data, setData] = useState<CustomerAccount[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchCustomerAccounts() {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<{ data: CustomerAccount[] }>(
        "/customer-accounts",
        {
          token: token ?? undefined,
        }
      );

      setData(response.data ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch customer accounts";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchCustomerAccounts();
  }, []);

  return {
    customerAccounts: data,
    isLoading,
    error,
    refetch: fetchCustomerAccounts,
  };
}