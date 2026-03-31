export type LoadStatus =
  | "new"
  | "docs_received"
  | "extracting"
  | "needs_review"
  | "validated"
  | "ready_to_submit"
  | "submitted"
  | "funded"
  | "paid"
  | "exception"
  | "archived";

export type LoadProcessingStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed";

export type Load = {
  id: string;
  load_number: string;
  status: LoadStatus;

  processing_status?: LoadProcessingStatus | null;

  customer_account_id?: string | null;
  driver_id?: string | null;
  broker_id?: string | null;

  rate_confirmation_number?: string | null;
  bol_number?: string | null;
  invoice_number?: string | null;

  broker_name_raw?: string | null;
  broker_email_raw?: string | null;

  pickup_date?: string | null;
  delivery_date?: string | null;

  pickup_location?: string | null;
  delivery_location?: string | null;

  gross_amount?: number | null;
  currency_code?: string | null;

  documents_complete?: boolean | null;
  has_ratecon?: boolean | null;
  has_bol?: boolean | null;
  has_invoice?: boolean | null;

  extraction_confidence_avg?: number | null;

  last_reviewed_by?: string | null;
  last_reviewed_at?: string | null;

  submitted_at?: string | null;
  funded_at?: string | null;
  paid_at?: string | null;

  notes?: string | null;

  created_at?: string | null;
  updated_at?: string | null;
};