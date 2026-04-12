import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type DashboardMetrics = {
  loads_total: number;
  loads_needing_review: number;
  loads_validated: number;
  loads_paid: number;
  documents_pending_processing: number;
  critical_validation_issues: number;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (trimmed.length === 0) {
      return 0;
    }

    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

function normalizeDashboardMetrics(payload: unknown): DashboardMetrics | null {
  const root = asRecord(payload);
  if (!root) {
    return null;
  }

  const nestedData = asRecord(root.data);
  const source = nestedData ?? root;

  return {
    loads_total: asNumber(source.loads_total),
    loads_needing_review: asNumber(source.loads_needing_review),
    loads_validated: asNumber(source.loads_validated),
    loads_paid: asNumber(source.loads_paid),
    documents_pending_processing: asNumber(source.documents_pending_processing),
    critical_validation_issues: asNumber(source.critical_validation_issues),
  };
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  const token = getAccessToken();
  const organizationId = getOrganizationId();

  if (!organizationId) {
    throw new Error("Missing organization context.");
  }

  const response = await apiClient.get<unknown>("/dashboard", {
    token: token ?? undefined,
    organizationId,
  });

  const normalized = normalizeDashboardMetrics(response);

  if (!normalized) {
    throw new Error("Dashboard response did not include usable metrics.");
  }

  return normalized;
}