import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type MoneyDashboardResponse = {
  summary: Record<string, string | number>;
  aging_buckets: Array<{ bucket: string; count: number; amount: string }>;
  status_breakdown: Array<{ status: string; count: number; amount: string }>;
  factoring_vs_direct: {
    factored: { count: number; amount: string };
    direct: { count: number; amount: string };
    advance_total: string;
    reserve_pending_total: string;
    direct_unpaid_total: string;
  };
  needs_attention: {
    urgent_count: number;
    overdue_followups_count: number;
    top_items: Array<{
      load_id: string;
      load_number: string | null;
      task_type: string;
      priority: string;
      due_at: string;
      recommended_action: string | null;
    }>;
  };
  recent_cash_activity: Array<{
    load_number: string | null;
    amount_received: string;
    paid_date: string;
    payment_status: string;
    factoring_used: boolean;
  }>;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

export async function getMoneyDashboard(params?: {
  dateFrom?: string;
  dateTo?: string;
}): Promise<MoneyDashboardResponse> {
  const token = getAccessToken();
  const organizationId = getOrganizationId();

  if (!organizationId) {
    throw new Error("Missing organization context.");
  }

  const query = new URLSearchParams();
  if (params?.dateFrom) query.set("date_from", params.dateFrom);
  if (params?.dateTo) query.set("date_to", params.dateTo);

  const suffix = query.toString().length > 0 ? `?${query.toString()}` : "";
  const payload = await apiClient.get<unknown>(`/reports/money-dashboard${suffix}`, {
    token: token ?? undefined,
    organizationId,
  });

  const root = asRecord(payload);
  const nestedData = asRecord(root?.data);
  const source = nestedData ?? root;

  if (!source) {
    throw new Error("Money dashboard response did not include usable data.");
  }

  return source as unknown as MoneyDashboardResponse;
}
