"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type Driver = {
  id: string;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
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

function asBoolean(value: unknown): boolean | null {
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
    return null;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();

    if (["true", "1", "yes", "y", "active"].includes(normalized)) {
      return true;
    }

    if (["false", "0", "no", "n", "inactive"].includes(normalized)) {
      return false;
    }
  }

  return null;
}

function normalizeDriver(item: unknown): Driver | null {
  const record = asRecord(item);

  if (!record) {
    return null;
  }

  const id = asString(record.id) ?? asString(record.driver_id);
  if (!id) {
    return null;
  }

  const firstName = asString(record.first_name) ?? asString(record.firstName);
  const lastName = asString(record.last_name) ?? asString(record.lastName);

  const combinedName = [firstName, lastName]
    .filter((part): part is string => Boolean(part))
    .join(" ")
    .trim();

  const fullName =
    asString(record.full_name) ??
    asString(record.fullName) ??
    asString(record.name) ??
    (combinedName.length > 0 ? combinedName : null) ??
    "Unknown driver";

  return {
    id,
    full_name: fullName,
    phone:
      asString(record.phone) ??
      asString(record.phone_number) ??
      asString(record.phoneNumber),
    email: asString(record.email),
    is_active:
      asBoolean(record.is_active) ??
      asBoolean(record.active) ??
      asBoolean(record.status) ??
      false,
  };
}



function normalizeDriversResponse(payload: unknown): Driver[] {
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
    } else if (Array.isArray(root.drivers)) {
      candidates.push(...root.drivers);
    } else if (Array.isArray(root.items)) {
      candidates.push(...root.items);
    } else if (Array.isArray(root.results)) {
      candidates.push(...root.results);
    }
  }

  return candidates
    .map((item) => normalizeDriver(item))
    .filter((item): item is Driver => item !== null)
    .sort((a, b) => a.full_name.localeCompare(b.full_name));
}

export function useDrivers(options?: { includeInactive?: boolean }) {
  const includeInactive = options?.includeInactive ?? false;
  const [data, setData] = useState<Driver[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  const fetchDrivers = useCallback(async (): Promise<void> => {
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

      const response = await apiClient.get<unknown>(`/drivers?page=1&page_size=200${includeInactive ? "" : "&is_active=true"}`, {
        token: token ?? undefined,
        organizationId,
        signal: controller.signal,
      });

      if (!isMountedRef.current) {
        return;
      }

      setData(normalizeDriversResponse(response));
    } catch (err: unknown) {
      if ((err as { name?: string })?.name === "AbortError") {
        return;
      }

      const message =
        err instanceof Error ? err.message : "Failed to fetch drivers";

      if (isMountedRef.current) {
        setError(message);
        setData([]);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [includeInactive]);

  useEffect(() => {
    isMountedRef.current = true;
    void fetchDrivers();

    return () => {
      isMountedRef.current = false;
      abortRef.current?.abort();
    };
  }, [fetchDrivers]);

  return {
    drivers: data,
    isLoading,
    error,
    refetch: fetchDrivers,
  };
}
