"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type PacketReadiness = {
  readiness_state?: string | null;
  ready_for_invoice?: boolean | null;
  ready_to_submit?: boolean | null;
  present_documents?: string[] | null;
  missing_required_documents?: {
    invoice?: string[] | null;
    submission?: string[] | null;
  } | null;
  blockers?: string[] | null;
  notes?: string[] | null;
};

export type Load = {
  id: string;
  load_number: string | null;
  status: string;
  source_channel?: string | null;
  processing_status?: string | null;
  gross_amount?: number | string | null;
  currency_code?: string | null;
  broker_id?: string | null;
  broker_name?: string | null;
  broker_name_raw?: string | null;
  broker_email_raw?: string | null;
  customer_account_id?: string | null;
  customer_account_name?: string | null;
  driver_id?: string | null;
  driver_name?: string | null;
  pickup_location?: string | null;
  delivery_location?: string | null;
  pickup_date?: string | null;
  delivery_date?: string | null;
  has_ratecon?: boolean | null;
  has_bol?: boolean | null;
  has_invoice?: boolean | null;
  documents_complete?: boolean | null;
  packet_readiness?: PacketReadiness | null;
  follow_up_required?: boolean | null;
  next_follow_up_at?: string | null;
  follow_up_owner_id?: string | null;
  follow_up_owner_name?: string | null;
  last_contacted_at?: string | null;
  submitted_at?: string | null;
  operational?: {
    queue?: string;
    queues?: string[];
    next_action?: { code?: string; label?: string };
    is_overdue?: boolean;
    days_in_state?: number | null;
    priority_score?: number;
    blockers?: string[];
  } | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

type ApiResponse<T> = {
  data: T;
  meta?: Record<string, unknown>;
  error?: ApiError | null;
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
  if (!id) {
    return null;
  }

  return {
    id,
    load_number:
      asString(record.load_number) ??
      asString(record.loadNumber) ??
      asString(record.number),
    status: asString(record.status) ?? "unknown",
    source_channel:
      asString(record.source_channel) ??
      asString(record.sourceChannel),
    processing_status:
      asString(record.processing_status) ??
      asString(record.processingStatus),
    gross_amount:
      asGrossAmount(record.gross_amount) ??
      asGrossAmount(record.grossAmount) ??
      asGrossAmount(record.amount),
    currency_code:
      asString(record.currency_code) ??
      asString(record.currencyCode),
    broker_id:
      asString(record.broker_id) ??
      asString(record.brokerId),
    broker_name:
      asString(record.broker_name) ??
      asString(record.brokerName),
    broker_name_raw:
      asString(record.broker_name_raw) ??
      asString(record.brokerNameRaw) ??
      asString(record.broker_name) ??
      asString(record.brokerName),
    broker_email_raw:
      asString(record.broker_email_raw) ??
      asString(record.brokerEmailRaw) ??
      asString(record.brokerEmail),
    customer_account_id:
      asString(record.customer_account_id) ??
      asString(record.customerAccountId),
    customer_account_name:
      asString(record.customer_account_name) ??
      asString(record.customerAccountName),
    driver_id:
      asString(record.driver_id) ??
      asString(record.driverId),
    driver_name:
      asString(record.driver_name) ??
      asString(record.driverName),
    pickup_location:
      asString(record.pickup_location) ??
      asString(record.pickupLocation),
    delivery_location:
      asString(record.delivery_location) ??
      asString(record.deliveryLocation),
    pickup_date:
      asString(record.pickup_date) ??
      asString(record.pickupDate),
    delivery_date:
      asString(record.delivery_date) ??
      asString(record.deliveryDate),
    has_ratecon: asOptionalBoolean(record.has_ratecon),
    has_bol: asOptionalBoolean(record.has_bol),
    has_invoice: asOptionalBoolean(record.has_invoice),
    documents_complete: asOptionalBoolean(record.documents_complete),
    packet_readiness: (record.packet_readiness as PacketReadiness | null | undefined) ?? null,
    follow_up_required: asOptionalBoolean(record.follow_up_required),
    next_follow_up_at: asString(record.next_follow_up_at) ?? asString(record.nextFollowUpAt),
    follow_up_owner_id:
      asString(record.follow_up_owner_id) ?? asString(record.followUpOwnerId),
    follow_up_owner_name:
      asString(record.follow_up_owner_name) ?? asString(record.followUpOwnerName),
    last_contacted_at:
      asString(record.last_contacted_at) ?? asString(record.lastContactedAt),
    submitted_at: asString(record.submitted_at) ?? asString(record.submittedAt),
    operational: (record.operational as Load["operational"]) ?? null,
    notes: asString(record.notes),
    created_at:
      asString(record.created_at) ??
      asString(record.createdAt),
    updated_at:
      asString(record.updated_at) ??
      asString(record.updatedAt),
  };
}

function normalizeLoadsResponse(payload: unknown): Load[] {
  if (Array.isArray(payload)) {
    return payload
      .map((item) => normalizeLoad(item))
      .filter((item): item is Load => item !== null);
  }

  const root = asRecord(payload);
  if (!root) {
    return [];
  }

  const candidates = Array.isArray(root.data)
    ? root.data
    : Array.isArray(root.loads)
      ? root.loads
      : Array.isArray(root.items)
        ? root.items
        : Array.isArray(root.results)
          ? root.results
          : [];

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
      const organizationId = getOrganizationId();

      const response = await apiClient.get<ApiResponse<unknown>>("/loads", {
        token: token ?? undefined,
        organizationId: organizationId ?? undefined,
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
