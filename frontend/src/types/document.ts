export type DocumentType =
  | "unknown"
  | "rate_confirmation"
  | "bill_of_lading"
  | "proof_of_delivery"
  | "invoice"
  | "other";

export type ProcessingStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "needs_review";

export type Document = {
  id: string;
  original_filename: string;
  document_type: DocumentType;
  processing_status: ProcessingStatus;

  mime_type?: string | null;
  source_channel?: string | null;
  storage_key?: string | null;

  linked_load_id?: string | null;
  uploaded_by_id?: string | null;

  classification_confidence?: number | null;
  uploaded_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};