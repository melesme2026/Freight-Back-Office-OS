export type InvoiceStatus = "draft" | "open" | "paid" | "past_due" | "void";

export type InvoiceLine = {
  id: string;
  line_type: string;
  description: string;
  quantity: number;
  unit_price: number;
  line_total: number;
};

export type Invoice = {
  id: string;
  invoice_number: string;
  customer_account_id: string;
  status: InvoiceStatus;
  currency_code: string;

  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  amount_due: number;

  issued_at?: string | null;
  due_at?: string | null;
  paid_at?: string | null;

  billing_period_start?: string | null;
  billing_period_end?: string | null;

  notes?: string | null;
  lines?: InvoiceLine[];
};