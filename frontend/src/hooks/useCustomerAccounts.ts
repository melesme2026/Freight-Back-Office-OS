"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type CustomerAccount = {
  id: string;
  account_name: string;
  account_code?: string | null;
  status: string;
  billing_email?: string | null;
  primary_contact_name?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
};

/* =========================
   Normalization Utilities
========================= */

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

function normalizeCustomerAccount(item: unknown): CustomerAccount | null {
  const record = asRecord(item);
  if (!record) return null;

  const id = asString(record.id);
  const accountName =
    asString(record.account_name) ??
    asString(record.accountName) ??
    asString(record.name);

  if (!id || !accountName) return null;

  return {
    id,
    account_name: accountName,
    account_code: asString(record.account_code) ?? asString(record.accountCode),
    status: asString(record.status) ?? "unknown",
    billing_email: asString(record.billing_email) ?? asString(record.billingEmail),
    primary_contact_name:
      asString(record.primary_contact_name) ?? asString(record.primaryContactName),
    primary_contact_email:
      asString(record.primary_contact_email) ?? asString(record.primaryContactEmail),
    primary_contact_phone:
      asString(record.primary_contact_phone) ?? asString(record.primaryContactPhone),
    notes: asString(record.notes),
    created_at: asString(record.created_at) ?? asString(record.createdAt) ?? undefined,
    updated_at: asString(record.updated_at) ?? asString(record.updatedAt) ?? undefined,
  };
}

function normalizeCustomerAccountsResponse(payload: unknown): CustomerAccount[] {
  const candidates: unknown[] = [];

  if (Array.isArray(payload)) {
    candidates.push(...payload);
  } else {
    const root = asRecord(payload);

    if (!root) return [];

    if (Array.isArray(root.data)) candidates.push(...root.data);
    else if (Array.isArray(root.customer_accounts)) candidates.push(...root.customer_accounts);
    else if (Array.isArray(root.items)) candidates.push(...root.items);
    else if (Array.isArray(root.results)) candidates.push(...root.results);
  }

  return candidates
    .map((item) => normalizeCustomerAccount(item))
    .filter((item): item is CustomerAccount => item !== null)
    .sort((a, b) => a.account_name.localeCompare(b.account_name));
}

/* =========================
   Hook
========================= */

export function useCustomerAccounts() {
  const [data, setData] = useState<CustomerAccount[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const fetchCustomerAccounts = useCallback(async (): Promise<void> => {
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

      const response = await apiClient.get<unknown>("/customer-accounts?page=1&page_size=200", {
        token: token ?? undefined,
        organizationId,
        signal: controller.signal,
      });

      if (!isMountedRef.current) return;

      setData(normalizeCustomerAccountsResponse(response));
    } catch (err: unknown) {
      if ((err as any)?.name === "AbortError") return;

      const message =
        err instanceof Error ? err.message : "Failed to fetch customer accounts";

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
    void fetchCustomerAccounts();

    return () => {
      isMountedRef.current = false;
      abortRef.current?.abort();
    };
  }, [fetchCustomerAccounts]);

  return {
    customerAccounts: data,
    isLoading,
    error,
    refetch: fetchCustomerAccounts,
  };
}