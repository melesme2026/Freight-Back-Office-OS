export type LoadStatus =
  | "draft"
  | "documents_pending"
  | "under_review"
  | "validated"
  | "submitted"
  | "invoiced"
  | "paid"
  | "closed";

export type Load = {
  id: string;
  load_number: string;
  status: LoadStatus;

  origin?: string | null;
  destination?: string | null;

  total_amount?: number | null;

  driver_id?: string | null;
  broker_id?: string | null;

  created_at?: string | null;
  updated_at?: string | null;
};