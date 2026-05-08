import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type Severity = "info" | "warning" | "critical";

export type CommandCenterKpis = {
  active_loads: number;
  loads_missing_docs: number;
  overdue_invoices: number;
  urgent_collections: number;
  pending_packet_sends: number;
  unresolved_packet_intelligence_blockers: number;
  factoring_reserve_pending: number;
  unpaid_total: string;
  factoring_reserve_pending_total: string;
};

export type CommandCenterAlert = {
  id: string;
  type: string;
  severity: Severity;
  priority_score: number;
  title: string;
  description: string;
  load_id: string;
  load_number: string | null;
  href: string;
};

export type MissingDocItem = {
  load_id: string;
  load_number: string | null;
  status: string;
  driver_name: string | null;
  broker_name: string | null;
  lane: string;
  delivery_date: string | null;
  missing_required_documents: string[];
  blocked_from_packet_send: boolean;
  packet_statuses: string[];
  unresolved_blockers: string[];
  severity: Severity;
  priority_score: number;
  reason: string;
};

export type CollectionItem = {
  load_id: string;
  load_number: string | null;
  invoice_number: string | null;
  broker_name: string | null;
  driver_name: string | null;
  lane: string;
  payment_status: string;
  factoring_status: string;
  reconciliation_status: string;
  expected_amount: string;
  amount_received: string;
  outstanding_amount: string;
  reserve_pending_amount: string;
  age_days: number;
  severity: Severity;
  priority_score: number;
  reason: string;
};

export type CommandCenterTask = {
  id: string;
  type: string;
  severity: Severity;
  priority_score: number;
  title: string;
  description: string;
  load_id: string;
  load_number: string | null;
  href: string;
};

export type PriorityCard = {
  key: string;
  label: string;
  count: number;
  severity: Severity;
  next_action: string;
};

export type CommandCenterData = {
  generated_at: string;
  kpis: CommandCenterKpis;
  alerts: CommandCenterAlert[];
  missing_docs: {
    summary: {
      total_loads: number;
      blocked_from_packet_send: number;
      by_document_type: Record<string, number>;
      critical_count: number;
      warning_count: number;
    };
    items: MissingDocItem[];
  };
  collections: {
    summary: {
      total_unpaid_items: number;
      urgent_count: number;
      overdue_count: number;
      unpaid_total: string;
      reserve_pending_total: string;
    };
    items: CollectionItem[];
  };
  tasks: {
    summary: {
      total: number;
      critical: number;
      warning: number;
      info: number;
    };
    items: CommandCenterTask[];
  };
  priority_cards: PriorityCard[];
  recent_activity: Array<{
    id: string;
    entity_type: string;
    entity_id: string;
    action: string;
    created_at: string;
  }>;
  meta: {
    load_limit: number;
    payment_limit: number;
    logic: string;
    not_implemented: string[];
  };
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

export async function getCommandCenter(): Promise<CommandCenterData> {
  const token = getAccessToken();
  const organizationId = getOrganizationId();

  if (!organizationId) {
    throw new Error("Missing organization context.");
  }

  const payload = await apiClient.get<unknown>("/operations/command-center", {
    token: token ?? undefined,
    organizationId,
  });

  const root = asRecord(payload);
  const data = asRecord(root?.data) ?? root;
  if (!data) {
    throw new Error("Command center response did not include usable data.");
  }

  return data as unknown as CommandCenterData;
}
