export type BillingCycle = "monthly" | "quarterly" | "yearly";

export type ServicePlan = {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  billing_cycle: BillingCycle;
  base_price: number;
  currency_code: string;
  per_load_price?: number | null;
  per_driver_price?: number | null;
  is_active: boolean;
};

export type SubscriptionStatus =
  | "trialing"
  | "active"
  | "past_due"
  | "cancelled"
  | "expired";

export type Subscription = {
  id: string;
  customer_account_id: string;
  service_plan_id: string;
  status: SubscriptionStatus;
  billing_email?: string | null;
  cancel_at_period_end: boolean;
  current_period_start?: string | null;
  current_period_end?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};