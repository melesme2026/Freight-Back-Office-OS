import { apiClient } from "@/lib/api-client";
import { getAccessToken, getOrganizationId } from "@/lib/auth";

export type AccountingExportKind = "invoices" | "factoring" | "settlements" | "payments" | "aging";

export type AccountingSettings = {
  mapping: {
    accounting_category: string;
    revenue_category: string;
    factoring_category: string;
    settlement_category: string;
    payment_category: string;
  };
  quickbooks: {
    provider: string;
    enabled: boolean;
    realm_id?: string | null;
    default_export_format: string;
    sync_mode: string;
    last_export_note?: string | null;
  };
  quickbooks_capabilities: {
    provider: string;
    sync_mode: string;
    supports_csv_exports: boolean;
    supports_direct_push: boolean;
    notes: string;
  };
};

type ApiResponse<T> = { data: T; meta?: Record<string, unknown>; error?: unknown };

type ExportFilters = {
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  reconciliationStatus?: string;
};

function authOptions() {
  const token = getAccessToken();
  const organizationId = getOrganizationId();
  if (!organizationId) throw new Error("Missing organization context.");
  return { token: token ?? undefined, organizationId };
}

export async function getAccountingSettings(): Promise<AccountingSettings> {
  const response = await apiClient.get<ApiResponse<AccountingSettings>>("/accounting/settings", authOptions());
  return response.data;
}

export async function updateAccountingSettings(payload: Partial<AccountingSettings>): Promise<AccountingSettings> {
  const response = await apiClient.patch<ApiResponse<AccountingSettings>>("/accounting/settings", payload, authOptions());
  return response.data;
}

export function accountingExportUrl(kind: AccountingExportKind, filters: ExportFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.status) params.set("status", filters.status);
  if (filters.reconciliationStatus) params.set("reconciliation_status", filters.reconciliationStatus);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return `/accounting/exports/${kind}.csv${suffix}`;
}

export async function downloadAccountingExport(kind: AccountingExportKind, filters: ExportFilters = {}): Promise<void> {
  const blob = await apiClient.getBlob(accountingExportUrl(kind, filters), authOptions());
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `accounting-${kind}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
