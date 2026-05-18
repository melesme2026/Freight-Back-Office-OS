import { getAccessToken, getOrganizationId } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";

export type Severity = "info" | "warning" | "critical";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export type CommandCenterKpis = {
  active_loads: number;
  loads_missing_docs: number;
  loads_ready_for_invoice?: number;
  loads_ready_to_submit?: number;
  overdue_invoices: number;
  urgent_collections: number;
  pending_packet_sends: number;
  unresolved_packet_intelligence_blockers: number;
  unresolved_validation_issues?: number;
  stalled_loads?: number;
  overdue_follow_ups?: number;
  stale_follow_ups?: number;
  drivers_missing_profile_items?: number;
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

export type BrokerBehaviorInsight = {
  broker_id: string;
  broker_name: string;
  trend: "stable" | "worsening";
  average_payment_days: number | null;
  current_unpaid_average_age_days: number;
  unpaid_invoice_count: number;
  overdue_invoice_count: number;
  dispute_or_short_paid_count: number;
  unreconciled_count: number;
  unpaid_total: string;
  overdue_total: string;
  reserve_pending_total: string;
  contributing_factors: string[];
  recommendation: string;
};

export type InvoiceRiskInsight = {
  load_id: string;
  load_number: string | null;
  invoice_number: string | null;
  broker_name: string | null;
  outstanding_amount: string;
  age_days: number;
  risk_level: RiskLevel;
  priority_score: number;
  risk_reasons: string[];
  contributing_factors: string[];
  recommended_action: string;
  payment_status: string;
  factoring_status: string;
  reconciliation_status: string;
  missing_required_documents: string[];
};

export type AssistantInsight = {
  id: string;
  type: string;
  severity: Severity;
  title: string;
  contributing_factors: string[];
  recommendation: string;
};

export type AssistantRecommendation = {
  id: string;
  type: string;
  severity: Severity;
  title: string;
  description: string;
  why: string;
  load_id?: string;
  load_number?: string | null;
  href: string;
  contributing_factors: string[];
  autonomous_action: false;
};

export type CollectionPriority = CollectionItem & {
  collection_rank_reason: string[];
  broker_trend: "stable" | "worsening" | "not_enough_history";
  recommended_action: string;
};


export type OperationalAttentionItem = {
  id?: string;
  source: "alert" | "task" | "follow_up" | "stalled_load" | string;
  type?: string;
  severity: Severity;
  priority_score: number;
  title?: string;
  description?: string | null;
  next_action?: string | null;
  load_id?: string;
  load_number?: string | null;
  href: string;
};

export type OperationalReadinessItem = {
  load_id: string;
  load_number: string | null;
  status: string;
  driver_name: string | null;
  broker_name: string | null;
  lane: string;
  readiness_state: string;
  ready_for_invoice: boolean;
  ready_to_submit: boolean;
  present_required_documents: Record<string, string[]>;
  missing_invoice_documents: string[];
  missing_submission_documents: string[];
  missing_recommended_documents: string[];
  blockers: string[];
  next_action: string;
  severity: Severity;
  priority_score: number;
  href: string;
};

export type OperationalFollowUpItem = {
  id: string;
  type: string;
  title: string;
  description: string | null;
  recommended_action: string | null;
  status: string;
  urgency: "upcoming" | "due_today" | "overdue" | "stale";
  due_at: string;
  age_days: number;
  load_id: string;
  load_number: string | null;
  severity: Severity;
  priority_score: number;
  href: string;
};

export type StalledLoadItem = {
  load_id: string;
  load_number: string | null;
  status: string;
  driver_name: string | null;
  lane: string;
  age_days: number;
  reason: string;
  next_action: string;
  severity: Severity;
  priority_score: number;
  href: string;
};

export type DriverVisibilityItem = {
  driver_id: string;
  driver_name: string;
  missing_items: string[];
  active_load_count: number;
  severity: Severity;
  priority_score: number;
  next_action: string;
  href: string;
};

export type OperationalIntelligence = {
  summary: {
    needs_attention_count: number;
    ready_to_invoice_count: number;
    ready_to_submit_count: number;
    invoice_blocked_count: number;
    packet_blocked_count: number;
    overdue_follow_up_count: number;
    stalled_load_count: number;
    driver_gap_count: number;
    unresolved_validation_issue_count: number;
    oldest_validation_issue_age_days: number;
  };
  needs_attention: OperationalAttentionItem[];
  readiness: {
    summary: {
      ready_to_invoice: number;
      ready_to_submit: number;
      blocked_invoice_readiness: number;
      blocked_packet_submission: number;
    };
    items: OperationalReadinessItem[];
  };
  follow_ups: {
    summary: { open: number; due_today: number; overdue: number; stale: number };
    items: OperationalFollowUpItem[];
  };
  stalled_loads: {
    summary: { total: number; critical: number; warning: number };
    items: StalledLoadItem[];
  };
  driver_visibility: {
    summary: { active_drivers: number; drivers_missing_profile_items: number; drivers_with_active_loads: number };
    items: DriverVisibilityItem[];
  };
  validation_issues: {
    unresolved_blocking_count: number;
    oldest_age_days: number;
    aging_over_3_days: number;
    by_severity: Record<string, number>;
  };
  guardrails: {
    uses_llm: false;
    invoice_math_changed: false;
    packet_readiness_rules_changed: false;
    source: string;
  };
};

export type AIOperationsAssistant = {
  summary: AssistantInsight[];
  invoice_risks: InvoiceRiskInsight[];
  broker_insights: BrokerBehaviorInsight[];
  collections_priorities: CollectionPriority[];
  recommendations: AssistantRecommendation[];
  explainability: {
    mode: "deterministic_rules_only";
    uses_llm: boolean;
    autonomous_actions: boolean;
    rules: string[];
  };
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
  operational_intelligence?: OperationalIntelligence;
  ai_operations_assistant?: AIOperationsAssistant;
  broker_behavior?: {
    summary: {
      broker_count: number;
      worsening_count: number;
      dispute_or_short_paid_count: number;
      unpaid_total: string;
      reserve_pending_total: string;
    };
    items: BrokerBehaviorInsight[];
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
    ai_assistant_logic?: string;
    not_implemented: string[];
  };
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

const emptyKpis: CommandCenterKpis = {
  active_loads: 0,
  loads_missing_docs: 0,
  loads_ready_for_invoice: 0,
  loads_ready_to_submit: 0,
  overdue_invoices: 0,
  urgent_collections: 0,
  pending_packet_sends: 0,
  unresolved_packet_intelligence_blockers: 0,
  unresolved_validation_issues: 0,
  stalled_loads: 0,
  overdue_follow_ups: 0,
  stale_follow_ups: 0,
  drivers_missing_profile_items: 0,
  factoring_reserve_pending: 0,
  unpaid_total: "0",
  factoring_reserve_pending_total: "0",
};

const emptyCommandCenter: CommandCenterData = {
  generated_at: new Date(0).toISOString(),
  kpis: emptyKpis,
  alerts: [],
  missing_docs: {
    summary: { total_loads: 0, blocked_from_packet_send: 0, by_document_type: {}, critical_count: 0, warning_count: 0 },
    items: [],
  },
  collections: {
    summary: { total_unpaid_items: 0, urgent_count: 0, overdue_count: 0, unpaid_total: "0", reserve_pending_total: "0" },
    items: [],
  },
  tasks: { summary: { total: 0, critical: 0, warning: 0, info: 0 }, items: [] },
  priority_cards: [],
  recent_activity: [],
  meta: { load_limit: 0, payment_limit: 0, logic: "fallback", not_implemented: [] },
};

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function asNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asString(value: unknown, fallback = "0"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function normalizeCommandCenterData(value: unknown): CommandCenterData {
  const data = asRecord(value) ?? {};
  const kpis = asRecord(data.kpis) ?? {};
  const missingDocs = asRecord(data.missing_docs) ?? {};
  const missingSummary = asRecord(missingDocs.summary) ?? {};
  const collections = asRecord(data.collections) ?? {};
  const collectionsSummary = asRecord(collections.summary) ?? {};
  const tasks = asRecord(data.tasks) ?? {};
  const tasksSummary = asRecord(tasks.summary) ?? {};

  return {
    ...emptyCommandCenter,
    ...data,
    generated_at: typeof data.generated_at === "string" ? data.generated_at : new Date().toISOString(),
    kpis: {
      ...emptyKpis,
      active_loads: asNumber(kpis.active_loads),
      loads_missing_docs: asNumber(kpis.loads_missing_docs),
      loads_ready_for_invoice: asNumber(kpis.loads_ready_for_invoice),
      loads_ready_to_submit: asNumber(kpis.loads_ready_to_submit),
      overdue_invoices: asNumber(kpis.overdue_invoices),
      urgent_collections: asNumber(kpis.urgent_collections),
      pending_packet_sends: asNumber(kpis.pending_packet_sends),
      unresolved_packet_intelligence_blockers: asNumber(kpis.unresolved_packet_intelligence_blockers),
      factoring_reserve_pending: asNumber(kpis.factoring_reserve_pending),
      unpaid_total: asString(kpis.unpaid_total),
      factoring_reserve_pending_total: asString(kpis.factoring_reserve_pending_total),
    },
    alerts: asArray<CommandCenterAlert>(data.alerts),
    missing_docs: {
      summary: {
        total_loads: asNumber(missingSummary.total_loads),
        blocked_from_packet_send: asNumber(missingSummary.blocked_from_packet_send),
        by_document_type: (asRecord(missingSummary.by_document_type) as Record<string, number> | null) ?? {},
        critical_count: asNumber(missingSummary.critical_count),
        warning_count: asNumber(missingSummary.warning_count),
      },
      items: asArray<MissingDocItem>(missingDocs.items),
    },
    collections: {
      summary: {
        total_unpaid_items: asNumber(collectionsSummary.total_unpaid_items),
        urgent_count: asNumber(collectionsSummary.urgent_count),
        overdue_count: asNumber(collectionsSummary.overdue_count),
        unpaid_total: asString(collectionsSummary.unpaid_total),
        reserve_pending_total: asString(collectionsSummary.reserve_pending_total),
      },
      items: asArray<CollectionItem>(collections.items),
    },
    tasks: {
      summary: {
        total: asNumber(tasksSummary.total),
        critical: asNumber(tasksSummary.critical),
        warning: asNumber(tasksSummary.warning),
        info: asNumber(tasksSummary.info),
      },
      items: asArray<CommandCenterTask>(tasks.items),
    },
    priority_cards: asArray<PriorityCard>(data.priority_cards),
    recent_activity: asArray<CommandCenterData["recent_activity"][number]>(data.recent_activity),
    meta: { ...emptyCommandCenter.meta, ...(asRecord(data.meta) ?? {}) } as CommandCenterData["meta"],
  } as CommandCenterData;
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

  return normalizeCommandCenterData(data);
}
