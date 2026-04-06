"use client";

import { useCallback, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

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
    .filter((item): item is Driver => item !== null);
}

export function useDrivers() {
  const [data, setData] = useState<Driver[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDrivers = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const token = getAccessToken();

      const response = await apiClient.get<unknown>("/drivers", {
        token: token ?? undefined,
      });

      setData(normalizeDriversResponse(response));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch drivers";
      setError(message);
      setData([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDrivers();
  }, [fetchDrivers]);

  return {
    drivers: data,
    isLoading,
    error,
    refetch: fetchDrivers,
  };
}