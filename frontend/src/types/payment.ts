export type PaymentStatus = "pending" | "succeeded" | "failed" | "refunded";

export type Payment = {
  id: string;
  billing_invoice_id?: string | null;
  customer_account_id: string;

  provider: string;
  status: PaymentStatus;

  amount: number;
  currency_code: string;

  external_reference?: string | null;
  failure_reason?: string | null;

  attempted_at?: string | null;
  succeeded_at?: string | null;
  failed_at?: string | null;

  created_at?: string | null;
  updated_at?: string | null;
};