"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";

export type Load = {
  id: string;
  load_number: string;
  status: string;
  gross_amount?: number | string | null;
  currency_code?: string | null;
  broker_name_raw?: string | null;
  broker_email_raw?: string | null;
  customer_account_id?: string | null;
  driver_id?: string | null;
  pickup_location?: string | null;
  delivery_location?: string | null;
  has_ratecon?: boolean | null;
  has_bol?: boolean | null;
  has_invoice?: boolean | null;
  notes?: string | null;
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

function asOptionalBoolean(value: unknown): boolean | null | undefined {
  if (value === undefined) {
    return undefined;
  }

  if (value === null) {
    return null;
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "number") {
    if (value === 1) {
      return true;
    }
    if (value === 0) {
      return false;
    }
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();

    if (normalized === "true" || normalized === "1" || normalized === "yes") {
      return true;
    }

    if (normalized === "false" || normalized === "0" || normalized === "no") {
      return false;
    }
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
    currency_code:
      asString(record.currency_code) ??
      asString(record.currencyCode),
    broker_name_raw:
      asString(record.broker_name_raw) ??
      asString(record.brokerName),
    broker_email_raw:
      asString(record.broker_email_raw) ??
      asString(record.brokerEmail),
    customer_account_id:
      asString(record.customer_account_id) ??
      asString(record.customerAccountId),
    driver_id:
      asString(record.driver_id) ??
      asString(record.driverId),
    pickup_location:
      asString(record.pickup_location) ??
      asString(record.pickupLocation),
    delivery_location:
      asString(record.delivery_location) ??
      asString(record.deliveryLocation),
    has_ratecon: asOptionalBoolean(record.has_ratecon),
    has_bol: asOptionalBoolean(record.has_bol),
    has_invoice: asOptionalBoolean(record.has_invoice),
    notes: asString(record.notes),
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
    } else if (Array.isArray(root.results)) {
      candidates.push(...root.results);
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