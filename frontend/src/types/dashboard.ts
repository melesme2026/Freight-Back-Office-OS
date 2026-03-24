export type DashboardMetric = {
  label: string;
  value: string | number;
  trend?: string;
};

export type DashboardSummary = {
  loads_in_progress?: number;
  needs_review?: number;
  open_invoices?: number;
  support_tickets?: number;
};

export type ReviewQueueSummary = {
  total_items?: number;
  high_severity?: number;
  resolved_today?: number;
};

export type BillingDashboardSummary = {
  active_subscriptions?: number;
  open_invoices?: number;
  past_due_invoices?: number;
  collected_this_month?: number;
};