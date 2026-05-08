import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type MoneyValue = string;

export type AnalyticsOption = { id: string; name: string };

export type RevenueTrend = {
  month: string;
  revenue: MoneyValue;
  paid_revenue: MoneyValue;
  unpaid_revenue: MoneyValue;
  invoice_count: number;
};

export type AgingBucket = {
  bucket: string;
  label: string;
  count: number;
  balance: MoneyValue;
};

export type InvoiceRiskItem = {
  load_id: string;
  load_number: string | null;
  invoice_number: string | null;
  broker_name: string | null;
  driver_name: string | null;
  lane: string;
  payment_status: string;
  factoring_status: string;
  reconciliation_status: string;
  expected_amount: MoneyValue;
  amount_received: MoneyValue;
  outstanding_amount: MoneyValue;
  age_days: number;
  reference_date: string;
};

export type PerformanceRow = {
  id: string;
  name: string;
  revenue: MoneyValue;
  paid_revenue: MoneyValue;
  unpaid_balance: MoneyValue;
  factored_revenue: MoneyValue;
  load_count: number;
  overdue_balance: MoneyValue;
  overdue_count: number;
  dispute_count: number;
  unreconciled_count: number;
  average_load_value: MoneyValue;
  average_payment_days?: number | null;
  profitability_note: string;
};

export type OperationalAnalyticsResponse = {
  filters: {
    date_from: string | null;
    date_to: string | null;
    broker_id: string | null;
    driver_id: string | null;
    factoring_status: string | null;
  };
  metric_definitions: Record<string, string>;
  revenue: {
    total_revenue: MoneyValue;
    paid_revenue: MoneyValue;
    received_revenue: MoneyValue;
    unpaid_revenue: MoneyValue;
    factored_revenue: MoneyValue;
    invoice_count: number;
    average_invoice_amount: MoneyValue;
    monthly_trends: RevenueTrend[];
  };
  unpaid_invoices: {
    unpaid_count: number;
    partially_paid_count: number;
    overdue_count: number;
    unpaid_total: MoneyValue;
    partially_paid_total: MoneyValue;
    overdue_total: MoneyValue;
    items: InvoiceRiskItem[];
  };
  aging_report: {
    buckets: AgingBucket[];
    total_count: number;
    total_balance: MoneyValue;
  };
  driver_profitability: PerformanceRow[];
  broker_performance: PerformanceRow[];
  lane_profitability: PerformanceRow[];
  collections: {
    unpaid_total: MoneyValue;
    overdue_balance: MoneyValue;
    reserve_pending_total: MoneyValue;
    unreconciled_count: number;
    unreconciled_balance: MoneyValue;
    dispute_count: number;
    short_paid_count: number;
    risk_summary: {
      high_risk_count: number;
      high_risk_balance: MoneyValue;
      medium_risk_count: number;
      medium_risk_balance: MoneyValue;
      low_risk_count: number;
      low_risk_balance: MoneyValue;
    };
    oldest_invoices: InvoiceRiskItem[];
  };
  filter_options: {
    brokers: AnalyticsOption[];
    drivers: AnalyticsOption[];
    factoring_statuses: string[];
  };
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

export async function getOperationalAnalytics(params?: {
  dateFrom?: string;
  dateTo?: string;
  brokerId?: string;
  driverId?: string;
  factoringStatus?: string;
}): Promise<OperationalAnalyticsResponse> {
  const token = getAccessToken();
  const organizationId = getOrganizationId();

  if (!organizationId) {
    throw new Error("Missing organization context.");
  }

  const query = new URLSearchParams();
  if (params?.dateFrom) query.set("date_from", params.dateFrom);
  if (params?.dateTo) query.set("date_to", params.dateTo);
  if (params?.brokerId) query.set("broker_id", params.brokerId);
  if (params?.driverId) query.set("driver_id", params.driverId);
  if (params?.factoringStatus) query.set("factoring_status", params.factoringStatus);

  const suffix = query.toString().length > 0 ? `?${query.toString()}` : "";
  const payload = await apiClient.get<unknown>(`/reports/operational-analytics${suffix}`, {
    token: token ?? undefined,
    organizationId,
  });

  const root = asRecord(payload);
  const nestedData = asRecord(root?.data);
  const source = nestedData ?? root;

  if (!source) {
    throw new Error("Analytics response did not include usable data.");
  }

  return source as unknown as OperationalAnalyticsResponse;
}
