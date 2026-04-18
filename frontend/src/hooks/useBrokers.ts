"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type BrokerRecord = {
  id: string;
  organization_id: string;
  name: string;
  mc_number?: string | null;
  email?: string | null;
  phone?: string | null;
  payment_terms_days?: number | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function asOptionalNumber(value: unknown): number | null | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function normalizeBroker(item: unknown): BrokerRecord | null {
  const row = asRecord(item);
  if (!row) {
    return null;
  }

  const id = asString(row.id);
  const organizationId = asString(row.organization_id);
  const name = asString(row.name);

  if (!id || !organizationId || !name) {
    return null;
  }

  return {
    id,
    organization_id: organizationId,
    name,
    mc_number: asString(row.mc_number),
    email: asString(row.email),
    phone: asString(row.phone),
    payment_terms_days: asOptionalNumber(row.payment_terms_days),
    notes: asString(row.notes),
    created_at: asString(row.created_at),
    updated_at: asString(row.updated_at),
  };
}

function normalizeBrokerList(payload: unknown): BrokerRecord[] {
  const root = asRecord(payload);
  const source = Array.isArray(root?.data)
    ? root?.data
    : Array.isArray(root?.items)
      ? root.items
      : [];

  return source
    .map((item) => normalizeBroker(item))
    .filter((item): item is BrokerRecord => item !== null);
}

export function useBrokers() {
  const [brokers, setBrokers] = useState<BrokerRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getAccessToken();
    const organizationId = getOrganizationId();

    if (!token || !organizationId) {
      setBrokers([]);
      setError("Missing session context. Please sign in again.");
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const payload = await apiClient.get<unknown>("/brokers?page=1&page_size=200", {
        token,
        organizationId,
      });

      setBrokers(normalizeBrokerList(payload));
    } catch (caught: unknown) {
      setBrokers([]);
      setError(caught instanceof Error ? caught.message : "Failed to load brokers.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    brokers,
    isLoading,
    error,
    refetch: load,
  };
}
